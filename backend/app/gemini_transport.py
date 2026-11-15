"""Gemini wire schema, separated from authoritative scientific validation.

google-genai's response_schema conversion maps extra='forbid' to
additional_properties, which this Gemini endpoint rejects. These transport models
deliberately omit that wire keyword. Raw output still undergoes strict canonical
validation, so unknown/missing fields never become accepted scientific proposals.
"""
import json
from pydantic import BaseModel, ValidationError
from app.intelligence_schemas import ResearchIntelligenceResponse, ScientificProposal, ProposalAction, RelationshipType

def proposal_errors(exc):
    errors=[]
    for item in exc.errors(include_input=False,include_url=False):
        path='.'.join(str(v) for v in item['loc'])
        kind=item['type']
        message=item['msg']
        if path=='action_type':message='Choose a supported research action, such as create_hypothesis or propose_experiment; research mode labels are not action types.'
        elif kind=='missing':message=f'Provide the required {path.replace("_"," ")} field.'
        elif kind=='extra_forbidden':message=f'Remove unsupported field {path}; the server supplies record identity, review status and provenance.'
        else:message=f'{path.replace("_"," ")}: {message}'
        errors.append({'field':path,'type':kind,'message':message})
    return errors

class GeminiAdapterParameters(BaseModel):
    data_generating_world:str
    intervention_value:float
    sample_count:int
    seed:int

class GeminiProposal(BaseModel):
    action_type:ProposalAction
    title:str
    content:str
    rationale:str
    assumptions:list[str]
    predictions:list[str]
    limitations:list[str]
    referenced_object_ids:list[str]
    target_object_id:str|None
    adapter_id:str|None
    adapter_parameters:GeminiAdapterParameters|None
    evidence_ids:list[str]
    source_object_id:str|None=None
    relationship_type:RelationshipType|None=None

class GeminiScientificResponse(BaseModel):
    answer:str
    uncertainties:list[str]
    context_references:list[str]
    proposals:list[GeminiProposal]
    limitations:list[str]

def normalize_gemini_response(text, schema=ResearchIntelligenceResponse):
    raw=json.loads(text)
    if not isinstance(raw,dict) or not isinstance(raw.get('proposals'),list):raise ValueError('Missing proposals array')
    if len(raw['proposals'])>3:raise ValueError('Too many proposals')
    # Validate the answer/envelope strictly, then each proposal independently.
    # Empty proposals is legitimate; no required proposal fields are invented.
    response=schema.model_validate({**raw,'proposals':[]})
    proposals=[];rejected=[]
    for index,item in enumerate(raw['proposals']):
        try:proposals.append(ScientificProposal.model_validate(item))
        except ValidationError as exc:
            errors=proposal_errors(exc)
            rejected.append({'index':index,'reason':' '.join(e['message'] for e in errors[:3]),'errors':errors,'_candidate':item})
    return schema.model_validate({**response.model_dump(),'proposals':[p.model_dump() for p in proposals]}),rejected
