"""SDK details only. No database access or scientific mutation authority."""
import json
import os
import time
import logging
import re
from dataclasses import replace
from dataclasses import dataclass, field
from typing import Protocol
from pydantic import ValidationError
from app.intelligence_schemas import ResearchIntelligenceResponse

class ProviderError(Exception):
    def __init__(self,code,message):self.code,self.message=code,message;super().__init__(message)
@dataclass
class ModelRequest:
    model:str
    system:str
    message:str
    context:dict
    history:list
    max_output_tokens:int=3000
    timeout:float=30
    generation_parameters:dict=field(default_factory=dict)
    schema:type=ResearchIntelligenceResponse
    correction_attempt:bool=False
    def payload(self):
        payload=json.dumps({'user_request':self.message,'project_context_untrusted':self.context,'conversation_history_untrusted':self.history},ensure_ascii=False)
        for variable in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY']:
            secret=os.getenv(variable)
            if secret:payload=payload.replace(json.dumps(secret,ensure_ascii=False)[1:-1],'[credential redacted]')
        return payload
@dataclass
class ModelResponse:
    output:ResearchIntelligenceResponse
    usage:dict|None=None
    rejected_proposals:list=field(default_factory=list)
    proposal_indices:list|None=None
    correction:dict=field(default_factory=dict)
class ResearchModelProvider(Protocol):
    def generate_structured_response(self,request:ModelRequest)->ModelResponse:...
def bounded_retry(method):
    def generate(self,request):
        deadline=time.monotonic()+request.timeout
        attempts=1 if request.correction_attempt else 2
        for attempt in range(attempts):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ProviderError('timeout','Provider request timed out; no scientific changes were made.')
            try:return method(self,replace(request,timeout=min(request.timeout/2,remaining)))
            except ProviderError as exc:
                if attempt==attempts-1 or exc.code not in ['timeout','provider_failure']:raise
    return generate

def safe_error(exc):
    # Never return SDK exception text: it can contain credentials, URLs or request data.
    status=getattr(exc,'status_code',None) or getattr(exc,'code',None)
    name=type(exc).__name__.lower()
    if status in [401,403]:return ProviderError('authentication','Provider authentication failed. Check the server API key and account permissions.')
    if status==429:return ProviderError('rate_limit','Provider rate limit or quota exhausted. Check quota and retry later.')
    if 'timeout' in name:return ProviderError('timeout','Provider request timed out. Retry with a new request key when ready.')
    if status in [400,404,422]:return ProviderError('model_or_schema','Provider rejected the selected model or structured-output schema. Verify the configured model supports native structured output.')
    if isinstance(exc,(ValidationError,ValueError)):return ProviderError('invalid_output','Provider returned incomplete, refused, or invalid structured output. No scientific changes were made.')
    return ProviderError('provider_failure','Provider network/service request failed. Check connectivity and configuration, then retry.')

logger=logging.getLogger('vectorheart.providers')
def sanitized_provider_detail(exc):
    # Prefer the provider's short message, never its HTTP request, headers or body.
    message=str(getattr(exc,'message',None) or str(exc))
    for key in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY']:
        secret=os.getenv(key)
        if secret:message=message.replace(secret,'[redacted]')
    message=re.sub(r'(?i)(?:api[_-]?key|authorization|bearer)([\s:=]+)[^\s,\'"}]+',r'credential\1[redacted]',message)
    message=re.sub(r'https?://\S+','[provider URL omitted]',message)
    # Error messages sometimes quote rejected source text. Keep schema diagnostics,
    # otherwise expose only the safe classification in logs.
    if not any(word in message.lower() for word in ['schema','additional_properties','additionalproperties','generation_config','model','quota','rate','unavailable','deadline','overload','permission','api key']):return '[provider detail omitted]'
    return message[:2000]

def gemini_error(exc,model,stage):
    status=getattr(exc,'status_code',None) or getattr(exc,'code',None)
    try:status=int(status) if status is not None else None
    except (ValueError,TypeError):status=None
    detail='Canonical validation failed; source values omitted.' if isinstance(exc,ValidationError) else sanitized_provider_detail(exc)
    logger.warning('Gemini failure stage=%s http_status=%s error_type=%s model=%s message=%s',stage,status,type(exc).__name__,model,detail)
    if isinstance(exc,ProviderError):return exc
    if status in [401,403] or (status==400 and any(word in detail.lower() for word in ['api key','api_key','api-key','api_key_invalid'])):return ProviderError('authentication','Gemini API key or permissions are invalid. Check the Python server credentials.')
    if status==429:return ProviderError('rate_limit','Gemini rate limit or quota reached. Retry later or check your account quota.')
    if status in [408,504] or 'timeout' in type(exc).__name__.lower():return ProviderError('timeout','Gemini request timed out. Retry later; no scientific changes were made.')
    if status in [500,502,503]:return ProviderError('model_unavailable','Gemini model is unavailable or overloaded. Retry later; the selected model was not changed.')
    if status==404:return ProviderError('model_unavailable','The selected Gemini model is unavailable or inaccessible to this account.')
    if stage=='internal_schema_validation':return ProviderError('internal_validation','Gemini response failed VECTORHEART scientific schema validation. No invalid scientific proposals were accepted.')
    if stage=='response_parsing':return ProviderError('invalid_output','Gemini returned an incomplete, refused, or invalid JSON response. Retry the request.')
    if status in [400,422] and any(word in detail.lower() for word in ['schema','generation_config','additional_properties','additionalproperties']):return ProviderError('schema_rejected','Gemini rejected the structured-output transport schema. Check the server diagnostic log.')
    if status in [400,422] or stage=='request_validation':return ProviderError('request_invalid','Gemini rejected the request configuration. Check the selected model and server diagnostic log.')
    return ProviderError('provider_failure','Gemini network or service request failed. Retry later; no scientific changes were made.')

class OpenAIProvider:
    @bounded_retry
    def generate_structured_response(self,r):
        from openai import OpenAI
        try:
            with OpenAI(api_key=os.environ['OPENAI_API_KEY'],timeout=r.timeout,max_retries=0) as client:
                response=client.responses.parse(model=r.model,instructions=r.system,input=r.payload(),text_format=r.schema,max_output_tokens=r.max_output_tokens,store=False)
                if response.status!='completed' or response.output_parsed is None:raise ValueError('Incomplete or refused')
                return ModelResponse(r.schema.model_validate(response.output_parsed.model_dump()),response.usage.model_dump() if response.usage else None)
        except Exception as exc:raise safe_error(exc) from None
class AnthropicProvider:
    @bounded_retry
    def generate_structured_response(self,r):
        from anthropic import Anthropic
        try:
            with Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'],timeout=r.timeout,max_retries=0) as client:
                response=client.messages.parse(model=r.model,system=r.system,messages=[{'role':'user','content':r.payload()}],max_tokens=r.max_output_tokens,output_format=r.schema)
                if response.stop_reason!='end_turn' or response.parsed_output is None:raise ValueError('Incomplete or refused')
                return ModelResponse(r.schema.model_validate(response.parsed_output.model_dump()),response.usage.model_dump() if response.usage else None)
        except Exception as exc:raise safe_error(exc) from None
class GeminiProvider:
    @bounded_retry
    def generate_structured_response(self,r):
        from google import genai
        from google.genai import types
        from app.gemini_transport import GeminiScientificResponse, normalize_gemini_response
        stage='request_validation'
        try:
            with genai.Client(api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=int(r.timeout*1000),retry_options=types.HttpRetryOptions(attempts=1))) as client:
                config=types.GenerateContentConfig(system_instruction=r.system,response_mime_type='application/json',response_schema=GeminiScientificResponse if r.schema is ResearchIntelligenceResponse else r.schema,max_output_tokens=r.max_output_tokens)
                stage='provider_generation'
                response=client.models.generate_content(model=r.model,contents=r.payload(),config=config)
                stage='response_parsing'
                if not response.candidates or str(response.candidates[0].finish_reason).split('.')[-1]!='STOP':raise ValueError('Incomplete or refused')
                # Distinguish malformed JSON from canonical validation failures.
                text=response.text or '';json.loads(text)
                stage='internal_schema_validation'
                if r.schema is ResearchIntelligenceResponse:
                    output,rejected=normalize_gemini_response(text,r.schema)
                else:
                    output,rejected=r.schema.model_validate_json(text),[]
                return ModelResponse(output,response.usage_metadata.model_dump(mode='json') if response.usage_metadata else None,rejected)
        except Exception as exc:raise gemini_error(exc,r.model,stage) from None
PROVIDERS={'OpenAI':(OpenAIProvider,'OPENAI'),'Anthropic':(AnthropicProvider,'ANTHROPIC'),'Google Gemini':(GeminiProvider,'GEMINI')}
def capabilities():
    return [{'provider':name,'credentials_configured':bool(os.getenv(prefix+'_API_KEY')),'default_model':os.getenv(prefix+'_DEFAULT_MODEL') or None,'available':bool(os.getenv(prefix+'_API_KEY') and os.getenv(prefix+'_DEFAULT_MODEL')),'structured_output':'native; model support checked by provider on request'} for name,(_,prefix) in PROVIDERS.items()]
def route(settings,role):
    assignment=settings.get('modelAssignments',{}).get(role,{})
    chosen=assignment.get('provider','Automatic');model=(assignment.get('modelId') or '').strip()
    if chosen=='Automatic':
        names=[s.strip() for s in os.getenv('VECTORHEART_PROVIDER_PRIORITY','OpenAI,Google Gemini,Anthropic').split(',')]
        chosen=next((name for name in names if name in PROVIDERS and os.getenv(PROVIDERS[name][1]+'_API_KEY') and os.getenv(PROVIDERS[name][1]+'_DEFAULT_MODEL')),None)
        if chosen is None:raise ProviderError('configuration','No automatic provider is configured. Set a server API key and default model, or choose a configured provider/model in project settings.')
        model='' # Automatic uses each provider's own server default.
    if chosen not in PROVIDERS:raise ProviderError('configuration','The selected provider is not implemented. Choose OpenAI, Anthropic or Google Gemini.')
    cls,prefix=PROVIDERS[chosen]
    if not os.getenv(prefix+'_API_KEY'):raise ProviderError('configuration',f'{chosen} is missing {prefix}_API_KEY on the Python server. No fallback was used.')
    model=model or os.getenv(prefix+'_DEFAULT_MODEL','').strip()
    if not model:raise ProviderError('configuration',f'Set a project model identifier or {prefix}_DEFAULT_MODEL on the Python server.')
    return chosen,model,cls()
