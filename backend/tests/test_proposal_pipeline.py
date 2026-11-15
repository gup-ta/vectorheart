import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.intelligence_schemas import ResearchIntelligenceResponse,ScientificProposal,proposal_contract
from app.gemini_transport import GeminiScientificResponse,normalize_gemini_response
from app.model_providers import ModelResponse,ModelRequest
from app.proposal_correction import correct_proposals
import app.intelligence as intelligence

def proposal(action='create_hypothesis',**patch):
    return {'action_type':action,'title':'Testable hypothesis','content':'Outdoor light exposure affects progression independently of near-work time.','rationale':'Separate correlated explanatory variables.','assumptions':['Confounding is controlled'],'predictions':['A discriminating comparison'],'limitations':['Synthetic source text; no measured clinical results'],'referenced_object_ids':[],'target_object_id':None,'adapter_id':None,'adapter_parameters':None,'evidence_ids':[],**patch}
def response(proposals):return {'answer':'Original scientific explanation.','uncertainties':[],'context_references':[],'proposals':proposals,'limitations':[]}
def result(proposals):
    output,rejected=normalize_gemini_response(json.dumps(response(proposals)));return ModelResponse(output,None,rejected)

def test_original_live_failure_is_an_action_enum_contract_mismatch():
    enum=GeminiScientificResponse.model_json_schema()['$defs']['GeminiProposal']['properties']['action_type']['enum']
    assert 'create_hypothesis' in enum and 'propose_experiment' in enum
    assert 'formalize_hypothesis' not in enum and 'Design Experiment' not in enum
    for wrong in ['formalize_hypothesis','Design Experiment']:
        r=result([proposal(wrong)])
        assert r.output.proposals==[]
        assert r.rejected_proposals[0]['errors'][0]['field']=='action_type'
        assert 'supported research action' in r.rejected_proposals[0]['reason']
    assert 'create_hypothesis' in proposal_contract() and '10000' in proposal_contract()

def test_one_targeted_correction_preserves_valid_siblings_and_original_science():
    original=proposal('formalize_hypothesis');good=proposal('create_question',title='A valid sibling')
    class Provider:
        calls=0
        def generate_structured_response(self,request):
            self.calls+=1;assert request.correction_attempt
            assert 'action_type' in request.message and 'literal_error' in request.message
            return result([proposal()])
    provider=Provider();r=correct_proposals(provider,ModelRequest('test','system','question',{},[]),result([original,good]))
    assert provider.calls==1 and r.correction['attempted']
    assert r.output.answer=='Original scientific explanation.'
    assert [p.action_type for p in r.output.proposals]==['create_hypothesis','create_question']
    assert r.output.proposals[0].content==original['content'] and r.rejected_proposals==[]
    assert r.proposal_indices==[0,1]

def test_correction_cannot_invent_reasoning_or_references_or_retry_indefinitely():
    class Provider:
        calls=0
        def generate_structured_response(self,request):self.calls+=1;return result([proposal(content='Invented replacement reasoning',referenced_object_ids=['invented-id'])])
    provider=Provider();r=correct_proposals(provider,ModelRequest('test','system','q',{},[]),result([proposal('formalize_hypothesis')]))
    assert provider.calls==1 and r.output.proposals==[] and r.rejected_proposals
    missing=proposal();del missing['rationale']
    r=correct_proposals(provider,ModelRequest('test','system','q',{},[]),result([missing]))
    assert provider.calls==1 and 'rationale' in r.rejected_proposals[0]['reason']
    assert '_candidate' not in r.rejected_proposals[0]

client=TestClient(app)
def post(path,data={}):
    r=client.post('/v1/'+path,json=data);assert r.status_code==200,r.text;return r.json()
def setup():
    pid=post('projects',{'title':'Proposal contract tests'})['id'];base=f'projects/{pid}'
    first=post(base+'/objects',{'projectId':pid,'type':'Hypothesis','title':'Outdoor light','body':'Outdoor light affects progression.'})
    second=post(base+'/objects',{'projectId':pid,'type':'Hypothesis','title':'Near-work confounding','body':'Near-work explains the association.'})
    cid=post(base+'/intelligence/conversations')['id'];return pid,base,cid,first,second
def mock_provider(monkeypatch,proposals):
    class Provider:
        def generate_structured_response(self,request):return result(proposals)
    monkeypatch.setattr(intelligence,'route',lambda *a:('Google Gemini','test-model',Provider()))
def turn(base,cid,key='proposal-contract-turn'):return post(base+f'/intelligence/conversations/{cid}/turns',{'message':'Propose a research action','idempotency_key':key})

def test_relationship_proposal_accepts_existing_graph_edge_with_provenance(monkeypatch):
    pid,base,cid,a,b=setup()
    mock_provider(monkeypatch,[proposal('propose_relationship',source_object_id=a['id'],target_object_id=b['id'],relationship_type='related_to',referenced_object_ids=[a['id'],b['id']])])
    r=turn(base,cid);assert len(r['proposals'])==1
    path=base+f"/intelligence/proposals/{r['proposals'][0]['id']}/accept"
    accepted=post(path);again=post(path);assert accepted['result_ids']==again['result_ids']
    relationships=client.get('/v1/'+base+'/relationships').json()
    assert len(relationships)==1 and relationships[0]['details']['model_provenance']['provider']=='Google Gemini'
    assert relationships[0]['source_object_id']==a['id'] and relationships[0]['target_object_id']==b['id']
    assert len(client.get('/v1/'+base+'/objects').json())==2

@pytest.mark.parametrize('patch',[
    {'source_object_id':'missing','target_object_id':'missing-too','relationship_type':'supports'},
    {'source_object_id':None,'target_object_id':None,'relationship_type':'supports'},
])
def test_invalid_relationships_are_withheld_without_mutation(monkeypatch,patch):
    pid,base,cid,a,b=setup();mock_provider(monkeypatch,[proposal('propose_relationship',**patch)])
    r=turn(base,cid);assert r['proposals']==[] and r['response_details']['rejected_proposals']
    assert client.get('/v1/'+base+'/relationships').json()==[]

def test_conceptual_experiment_and_observation_preserve_unverified_status(monkeypatch):
    pid,base,cid,a,b=setup()
    mock_provider(monkeypatch,[proposal('propose_experiment',target_object_id=a['id'],title='Clinical study design'),proposal('create_observation',title='Suggested observation to collect')])
    r=turn(base,cid)
    for p in r['proposals']:post(base+f"/intelligence/proposals/{p['id']}/accept")
    objects=client.get('/v1/'+base+'/objects').json();note=next(o for o in objects if o['title']=='Clinical study design');observation=next(o for o in objects if o['type']=='Observation')
    assert note['type']=='Note' and note['metadata']['conceptual_experiment']
    assert observation['metadata']['verification_status']=='unverified' and observation['metadata']['source_type']=='model_suggestion'
    assert client.get('/v1/'+base+'/runs').json()==[] and client.get('/v1/'+base+'/evidence').json()==[]

def test_repaired_proposals_persist_and_remain_acceptance_reviewable(monkeypatch):
    pid,base,cid,a,b=setup()
    class Provider:
        calls=0
        def generate_structured_response(self,request):
            self.calls+=1
            return result([proposal('create_hypothesis' if request.correction_attempt else 'formalize_hypothesis')])
    provider=Provider();monkeypatch.setattr(intelligence,'route',lambda *a:('Google Gemini','test-model',provider))
    r=turn(base,cid);assert len(r['proposals'])==1 and provider.calls==2
    assert r['provenance']['proposal_correction']['attempted']
    assert client.get('/v1/'+base+'/objects').json()[0]['id']==a['id']
    accepted=post(base+f"/intelligence/proposals/{r['proposals'][0]['id']}/accept");oid=accepted['result_ids']['object_id']
    obj=client.get('/v1/'+base+'/objects/'+oid).json();assert obj['type']=='Hypothesis' and obj['metadata']['model_provenance']['proposal_correction']['attempted']
    assert client.get('/v1/'+base+'/objects/'+oid+'/revisions').json()
