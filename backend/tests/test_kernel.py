from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.science import Parameters, simulate, predictions, validate_result
from pydantic import ValidationError
import pytest
client=TestClient(app)
def post(path,data={}):
    r=client.post('/v1/'+path,json=data);assert r.status_code==200,r.text;return r.json()
def test_cycle_persistence_and_approval():
    p=post('projects',{'title':'Test','description':''});pid=p['id'];base=f'projects/{pid}'
    post(base+'/demo')
    assert client.post('/v1/'+base+'/demo').status_code==409
    op=client.get('/v1/'+base+'/operations').json()[0];oid=op['id'];target=op['target_object_ids'][0]
    assert client.post(f'/v1/{base}/operations/{oid}/execute').status_code==409
    post(f'{base}/operations/{oid}/approve');post(f'{base}/operations/{oid}/execute');post(f'{base}/operations/{oid}/execute')
    runs=client.get('/v1/'+base+'/runs').json();assert len(runs)==1 and runs[0]['status']=='completed'
    assert all(runs[0]['validation_results'].values())
    evidence=client.get('/v1/'+base+'/evidence').json()[0];assert evidence['source_type']=='simulation'
    obj=client.get(f'/v1/{base}/objects/{target}').json()
    revision=post(base+'/operations',{'action_type':'modify.propose_hypothesis_revision','target_object_ids':[target],'proposal_payload':{'original_statement':obj['body'],'proposed_statement':'Supported only within the configured simulation.','evidence_ids':[evidence['id']],'scope':'Synthetic world A','remaining_uncertainties':['Real-world applicability'],'rationale':'Simulation evidence'}})
    assert client.get(f'/v1/{base}/objects/{target}').json()['body']==obj['body']
    post(f"{base}/operations/{revision['id']}/approve");post(f"{base}/operations/{revision['id']}/execute")
    history=client.get(f'/v1/{base}/objects/{target}/revisions').json();assert len(history)==2 and history[0]['body_snapshot']==obj['body']
    trail=client.get('/v1/'+base+'/events?limit=500').json();assert [e['project_sequence_number'] for e in trail]==list(range(1,len(trail)+1))
    with TestClient(app) as restarted: assert len(restarted.get('/v1/'+base+'/runs').json())==1
def test_import_is_idempotent_atomic_and_reports_dangling():
    raw={'id':'legacy','title':'Legacy','objects':[{'id':'legacy-note','projectId':'legacy','type':'Note','title':'Original','body':'Preserve'}],'relationships':[{'id':'dangling','sourceId':'absent','targetId':'legacy-note'}]}
    result=post('import',{'projects':[raw]});assert result['warnings']
    raw['title']='Stale overwrite';post('import',{'projects':[raw]})
    assert client.get('/v1/projects/legacy').json()['title']=='Legacy'
    broken={'id':'broken','title':'Broken','objects':[{'id':'foreign','projectId':'different','type':'Note','title':'','body':''}]}
    assert client.post('/v1/import',json={'projects':[broken]}).status_code==422
    assert client.get('/v1/projects/broken').status_code==404
def test_integrity_rejection_and_failure(monkeypatch):
    p=post('projects',{'title':'Integrity'});base='projects/'+p['id'];post(base+'/demo')
    note=post(base+'/objects',{'projectId':p['id'],'type':'Note','title':'Source','body':'Idea'})
    assert client.post('/v1/'+base+'/relationships',json={'sourceId':note['id'],'targetId':'missing'}).status_code==404
    assert client.post('/v1/'+base+'/objects',json={'projectId':p['id'],'type':'Invalid','title':'','body':''}).status_code==422
    op=post(base+'/operations',{'action_type':'construct.hypothesis_from_note','target_object_ids':[note['id']],'proposal_payload':{'statement':'A claim'}})
    post(base+'/operations/'+op['id']+'/reject')
    assert client.post('/v1/'+base+'/operations/'+op['id']+'/approve').status_code==409
    assert client.post('/v1/'+base+'/operations/'+op['id']+'/execute').status_code==409
    test=client.get('/v1/'+base+'/operations').json()[0];post(base+'/operations/'+test['id']+'/approve')
    import app.main as main
    monkeypatch.setattr(main.subprocess,'run',lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError('worker failed')))
    assert client.post('/v1/'+base+'/operations/'+test['id']+'/execute').status_code==422
    assert client.get('/v1/'+base+'/runs').json()[0]['errors']==['worker failed']
    assert client.get('/v1/'+base+'/evidence').json()==[]
def test_numerics():
    import numpy as np
    a=np.array([[1.,0.],[.8,.6]]);b=np.array([[.6,.8],[0.,1.]])
    assert np.allclose(a@a.T,b@b.T) and np.allclose(a@a.T,[[1,.8],[.8,1]])
    assert predictions(Parameters())=={'A':{'mean':1.6,'variance':.36},'B':{'mean':0.,'variance':1.}}
    assert simulate({})==simulate({})
    for raw in [{'sample_count':99},{'sample_count':5001},{'intervention_value':6},{'seed':-1},{'intervention_value':float('nan')}]:
        with pytest.raises(ValidationError):Parameters.model_validate(raw)
    result=simulate({});assert all(validate_result(result,{}).values());result['mean']=100
    with pytest.raises(ValueError):validate_result(result,{})
    result=simulate({});result['samples'][0]=float('nan')
    with pytest.raises(ValueError):validate_result(result,{})

def test_cross_project_and_immutable_results():
    p=post('projects',{'title':'One'});other=post('projects',{'title':'Two'})
    obj=post('projects/'+p['id']+'/objects',{'projectId':p['id'],'type':'Note','title':'Note','body':'Content'})
    foreign=post('projects/'+other['id']+'/objects',{'projectId':other['id'],'type':'Note','title':'Foreign','body':''})
    assert client.post('/v1/projects/'+p['id']+'/relationships',json={'sourceId':obj['id'],'targetId':foreign['id']}).status_code==404
    assert client.post('/v1/projects/'+p['id']+'/objects',json={'projectId':p['id'],'type':'Evidence','title':'Fake','body':'Invented'}).status_code==422
    op=post('projects/'+p['id']+'/operations',{'action_type':'construct.hypothesis_from_note','target_object_ids':[obj['id']],'proposal_payload':{'statement':'Constructed claim'}})
    post(f"projects/{p['id']}/operations/{op['id']}/approve");post(f"projects/{p['id']}/operations/{op['id']}/execute")
    assert client.get(f"/v1/projects/{p['id']}/objects/{obj['id']}").json()['body']=='Content'
    assert any(o['type']=='Hypothesis' for o in client.get(f"/v1/projects/{p['id']}/objects").json())

def test_database_survives_separate_process():
    import subprocess,sys,json
    p=post('projects',{'title':'Restart record'})
    code="from app.db import Session,Project; import json; s=Session(); print(json.dumps(s.get(Project,"+repr(p['id'])+").title))"
    result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)=='Restart record'
