import json
import logging
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.gemini_transport import GeminiScientificResponse, normalize_gemini_response
from app.intelligence_schemas import ResearchIntelligenceResponse, ScientificProposal
from app.model_providers import GeminiProvider, ModelRequest, ProviderError, gemini_error

def envelope(proposals=None):
    return {'answer':'A scientific explanation with explicitly limited evidence.','uncertainties':[],'context_references':[],'proposals':proposals or [],'limitations':['No empirical measurements were supplied.']}
def valid_proposal():
    return {'action_type':'create_hypothesis','title':'A testable hypothesis','content':'Water availability affects growth within a controlled range.','rationale':'A falsifiable prediction.','assumptions':['Controlled light'],'predictions':['Different growth under different water availability'],'limitations':['Requires actual measurements'],'referenced_object_ids':[],'target_object_id':None,'adapter_id':None,'adapter_parameters':None,'evidence_ids':[]}

def test_transport_omits_original_rejected_keyword_without_relaxing_canonical_schema():
    canonical=ResearchIntelligenceResponse.model_json_schema()
    transport=GeminiScientificResponse.model_json_schema()
    assert 'additionalProperties' in json.dumps(canonical)
    assert 'additionalProperties' not in json.dumps(transport)
    assert 'additional_properties' not in json.dumps(transport)
    assert ResearchIntelligenceResponse.model_config['extra']=='forbid'
    assert ScientificProposal.model_config['extra']=='forbid'

def test_real_sdk_converts_transport_without_rejected_keyword():
    # Exercise the installed SDK's actual schema conversion, not a mocked schema.
    from google.genai import types
    from google.genai import _transformers
    schema=_transformers.t_schema(None,GeminiScientificResponse)
    wire=schema.model_dump(mode='json',exclude_none=True)
    assert 'additional_properties' not in json.dumps(wire)
    assert wire['properties']['proposals']['items']['properties']['adapter_parameters']

def test_empty_proposals_and_strict_individual_proposal_validation():
    response,rejected=normalize_gemini_response(json.dumps(envelope()))
    assert response.proposals==[] and rejected==[]
    malformed=valid_proposal();del malformed['assumptions']
    unknown=valid_proposal();unknown['verification_status']='independently_replicated'
    response,rejected=normalize_gemini_response(json.dumps(envelope([valid_proposal(),malformed,unknown])))
    assert len(response.proposals)==1 and [r['index'] for r in rejected]==[1,2]
    assert response.answer==envelope()['answer']
    with pytest.raises((ValidationError,ValueError)):normalize_gemini_response(json.dumps({'answer':'No required fields'}))
    with pytest.raises((ValidationError,ValueError)):normalize_gemini_response(json.dumps(envelope([valid_proposal()]*4)))

@pytest.mark.parametrize('status,message,stage,expected',[
    (400,'Unknown name "additional_properties" at generation_config.response_schema','provider_generation','schema_rejected'),
    (503,'Model overloaded; high demand','provider_generation','model_unavailable'),
    (504,'Deadline exceeded','provider_generation','timeout'),
    (429,'Quota reached','provider_generation','rate_limit'),
    (403,'Permission denied','provider_generation','authentication'),
    (400,'API key not valid','provider_generation','authentication'),
    (404,'Model not found','provider_generation','model_unavailable'),
    (400,'Invalid generation parameter','provider_generation','request_invalid'),
    (None,'Invalid JSON','response_parsing','invalid_output'),
    (None,'Missing answer','internal_schema_validation','internal_validation'),
])
def test_error_categories(status,message,stage,expected):
    class SDKError(Exception):
        code=status
    assert gemini_error(SDKError(message),'gemini-3.5-flash-lite',stage).code==expected

def test_diagnostic_logs_keep_status_stage_and_message_without_credentials(monkeypatch,caplog):
    monkeypatch.setenv('GEMINI_API_KEY','private-api-key-value')
    class SDKError(Exception):code=400
    with caplog.at_level(logging.WARNING,logger='vectorheart.providers'):
        error=gemini_error(SDKError('Unknown additional_properties in response_schema; api_key=private-api-key-value'),'gemini-3.5-flash-lite','provider_generation')
    assert error.code=='schema_rejected'
    assert 'http_status=400' in caplog.text and 'stage=provider_generation' in caplog.text
    assert 'SDKError' in caplog.text and 'additional_properties' in caplog.text
    assert 'private-api-key-value' not in caplog.text and 'private-api-key-value' not in error.message
    try:ResearchIntelligenceResponse.model_validate({'answer':'private research model text'})
    except ValidationError as exc:
        with caplog.at_level(logging.WARNING,logger='vectorheart.providers'):gemini_error(exc,'model','internal_schema_validation')
    assert 'private research model text' not in caplog.text

def test_adapter_uses_transport_then_normalizes_and_reports_invalid_proposals(monkeypatch):
    from google import genai
    captured={};malformed=valid_proposal();malformed['action_type']='invent_evidence'
    def generate(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(candidates=[SimpleNamespace(finish_reason='STOP')],text=json.dumps(envelope([valid_proposal(),malformed])),usage_metadata=None)
    class Client:
        def __init__(self,**kwargs):self.models=SimpleNamespace(generate_content=generate)
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setenv('GEMINI_API_KEY','test-key');monkeypatch.setattr(genai,'Client',Client)
    response=GeminiProvider().generate_structured_response(ModelRequest('gemini-3.5-flash-lite','Scientific instructions','Question',{},[]))
    assert captured['config'].response_schema is GeminiScientificResponse
    assert len(response.output.proposals)==1 and response.rejected_proposals[0]['index']==1
    assert response.usage is None

def test_rejected_transport_proposal_reaches_existing_review_history(monkeypatch):
    from fastapi.testclient import TestClient
    import app.intelligence as intelligence
    from app.main import app
    from app.model_providers import ModelResponse
    class Provider:
        def generate_structured_response(self,r):
            output,rejected=normalize_gemini_response(json.dumps(envelope([{'action_type':'create_hypothesis'}])))
            return ModelResponse(output,None,rejected)
    monkeypatch.setattr(intelligence,'route',lambda *args:('Google Gemini','gemini-3.5-flash-lite',Provider()))
    client=TestClient(app)
    pid=client.post('/v1/projects',json={'title':'Disposable regression'}).json()['id']
    base=f'/v1/projects/{pid}/intelligence/conversations';cid=client.post(base).json()['id']
    turn=client.post(base+f'/{cid}/turns',json={'message':'Explain only','idempotency_key':'gemini-regression-key'}).json()
    assert turn['status']=='completed' and turn['proposals']==[]
    assert turn['response_details']['rejected_proposals'][0]['index']==0
    assert client.get(f'/v1/projects/{pid}/objects').json()==[]

def test_transport_and_scientific_rejections_keep_original_proposal_indices(monkeypatch):
    from fastapi.testclient import TestClient
    import app.intelligence as intelligence
    from app.main import app
    from app.model_providers import ModelResponse
    invalid_reference=valid_proposal();invalid_reference['referenced_object_ids']=['invented-object']
    class Provider:
        def generate_structured_response(self,r):
            output,rejected=normalize_gemini_response(json.dumps(envelope([{'title':'Missing fields'},invalid_reference,valid_proposal()])))
            return ModelResponse(output,None,rejected)
    monkeypatch.setattr(intelligence,'route',lambda *args:('Google Gemini','gemini-3.5-flash-lite',Provider()))
    client=TestClient(app);pid=client.post('/v1/projects',json={'title':'Mixed validation regression'}).json()['id']
    base=f'/v1/projects/{pid}/intelligence/conversations';cid=client.post(base).json()['id']
    response=client.post(base+f'/{cid}/turns',json={'message':'Propose hypotheses','idempotency_key':'mixed-validation-key'}).json()
    assert response['status']=='completed' and len(response['proposals'])==1
    assert [v['index'] for v in response['response_details']['rejected_proposals']]==[0,1]
