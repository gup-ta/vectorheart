"""Explicit, bounded Gemini checks in disposable storage; never run by pytest."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--diagnose',action='store_true');parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if not(args.diagnose or args.verify):parser.error('Choose --diagnose or --verify')
    from dotenv import load_dotenv
    load_dotenv(BACKEND/'.env',override=False)
    model=os.getenv('GEMINI_DEFAULT_MODEL') or 'gemini-3.5-flash-lite'
    if not os.getenv('GEMINI_API_KEY'):raise RuntimeError('Gemini credentials are unavailable')
    with tempfile.TemporaryDirectory(prefix='vectorheart-proposals-') as directory:
        os.environ['KERNEL_DB_PATH']=str(Path(directory)/'test.sqlite3')
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(BACKEND/'alembic.ini')),'head')
        from app.db import engine
        try:
            from fastapi.testclient import TestClient
            from app.main import app
            from app.intelligence_schemas import MODE_ROLES,ScientificProposal
            if args.diagnose:
                import app.gemini_transport as transport
                normalize=transport.normalize_gemini_response
                def inspect_synthetic(text,*a,**kw):
                    raw=json.loads(text)
                    print('SYNTHETIC RAW PROPOSALS',json.dumps(raw.get('proposals'),ensure_ascii=True),flush=True)
                    for i,p in enumerate(raw.get('proposals',[])):
                        try:ScientificProposal.model_validate(p);print('CANONICAL',i,'valid',flush=True)
                        except Exception as exc:print('CANONICAL',i,json.dumps(exc.errors(include_input=False,include_url=False)),flush=True)
                    return normalize(text,*a,**kw)
                transport.normalize_gemini_response=inspect_synthetic
            with TestClient(app) as client:
                def post(path,data={}):
                    r=client.post('/v1/'+path,json=data)
                    assert r.status_code==200,r.text
                    return r.json()
                settings={'modelAssignments':{r:{'provider':'Google Gemini','modelId':model} for r in MODE_ROLES.values()}}
                pid=post('projects',{'title':'Disposable myopia research','description':'Synthetic illustration; no private research or real measured data.','settings':settings})['id'];base=f'projects/{pid}'
                def obj(typ,title,body):return post(base+'/objects',{'projectId':pid,'type':typ,'title':title,'body':body})
                question=obj('Question','Outdoor exposure and myopia','Does outdoor exposure affect myopia progression independently of near-work time?')
                observation=obj('Observation','Synthetic association','Illustrative, unverified report: students spending more time outdoors had lower myopia incidence. Near-work time and baseline refraction may confound the association; these are not executed measurements.')
                hypothesis=obj('Hypothesis','Outdoor light hypothesis','Greater daily outdoor light exposure reduces myopia progression independently of near-work time.')
                alternative=obj('Hypothesis','Near-work confounding hypothesis','The association of outdoor exposure with myopia is explained by reduced near-work time.')
                cid=post(base+'/intelligence/conversations')['id']
                requests=[('Identify one unresolved assumption and propose a new testable hypothesis as a structured research action.',observation['id'],'Formalize'),('What experiment would test this hypothesis?',hypothesis['id'],'Design Experiment')]
                outputs=[]
                for i,(message,selected,mode) in enumerate(requests):
                    response=post(base+f'/intelligence/conversations/{cid}/turns',{'message':message,'selected_object_id':selected,'mode':mode,'idempotency_key':f'live-proposal-request-{i}'})
                    print('RESULT',model,response['status'],json.dumps(response['response_details']),flush=True);outputs.append(response)
                if args.verify:
                    assert all(r['status']=='completed' for r in outputs)
                    proposal=next(p for p in outputs[0]['proposals'] if p['action_type']=='create_hypothesis')
                    accepted=post(base+f"/intelligence/proposals/{proposal['id']}/accept")
                    again=post(base+f"/intelligence/proposals/{proposal['id']}/accept");assert again['result_ids']==accepted['result_ids']
                    oid=accepted['result_ids']['object_id'];created=client.get('/v1/'+base+'/objects/'+oid).json();assert created['type']=='Hypothesis' and created['metadata']['model_provenance']['model']==model
                    assert client.put('/v1/'+base+'/canvas/'+oid,json={'x':30,'y':60}).status_code==200
                    loaded=client.get('/v1/'+base).json();assert sum(o['id']==oid for o in loaded['objects'])==1;assert any(p['objectId']==oid for p in loaded['placements'])
                    revisions=client.get('/v1/'+base+'/objects/'+oid+'/revisions').json();assert revisions and revisions[0]['metadata_snapshot']['model_provenance']
                    exp=next(p for p in outputs[1]['proposals'] if p['action_type']=='propose_experiment');assert not exp['payload']['executable']
                    conceptual=post(base+f"/intelligence/proposals/{exp['id']}/accept");note=client.get('/v1/'+base+'/objects/'+conceptual['result_ids']['object_id']).json();assert note['type']=='Note' and note['metadata']['conceptual_experiment']
                    assert client.get('/v1/'+base+'/runs').json()==[]
                    print('VERIFIED live hypothesis acceptance, provenance, revisions, shared Notebook/Canvas identity, duplicate acceptance, conceptual study without execution.',flush=True)
                    relation=post(base+f'/intelligence/conversations/{cid}/turns',{'message':'Propose one scientifically justified relationship between the existing Outdoor light hypothesis and Near-work confounding hypothesis as a structured research action. Reference only existing objects; do not create or revise their content.','selected_object_id':hypothesis['id'],'mode':'Synthesize','idempotency_key':'live-relationship-request'})
                    assert relation['status']=='completed',relation['response_details']
                    rp=next(p for p in relation['proposals'] if p['action_type']=='propose_relationship')
                    edge=post(base+f"/intelligence/proposals/{rp['id']}/accept");rid=edge['result_ids']['relationship_id']
                    assert post(base+f"/intelligence/proposals/{rp['id']}/accept")['result_ids']['relationship_id']==rid
                    graph=client.get('/v1/'+base+'/relationships').json();assert any(r['id']==rid for r in graph)
                    print('VERIFIED live existing-object relationship proposal and idempotent acceptance.',flush=True)
                    post(base+'/demo')
                    causal=next(o for o in client.get('/v1/'+base+'/objects').json() if o['title']=='Hypothesis A')
                    executable=post(base+f'/intelligence/conversations/{cid}/turns',{'message':'For the selected First Heartbeat synthetic causal hypothesis only, propose one executable experiment using the registered causal intervention: do(X=2), world A, sample_count 1000, seed 42. Use the supplied tool schema and the actual selected hypothesis ID. This is not a myopia experiment.','selected_object_id':causal['id'],'mode':'Design Experiment','idempotency_key':'live-executable-request'})
                    assert executable['status']=='completed',executable['response_details']
                    ep=next(p for p in executable['proposals'] if p['action_type']=='propose_experiment' and p['payload']['executable'])
                    accepted=post(base+f"/intelligence/proposals/{ep['id']}/accept");opid=accepted['result_ids']['operation_id']
                    assert client.get('/v1/'+base+'/operations/'+opid).json()['status']=='draft'
                    assert client.post('/v1/'+base+'/operations/'+opid+'/execute').status_code==409
                    post(base+'/operations/'+opid+'/approve');post(base+'/operations/'+opid+'/execute')
                    run=client.get('/v1/'+base+'/runs').json()[0];assert run['status']=='completed' and all(run['validation_results'].values())
                    print('VERIFIED live executable proposal: draft, explicit approval, real computation, validated evidence.',flush=True)
        finally:engine.dispose()
    print('Temporary database removed; real research data untouched.',flush=True)
if __name__=='__main__':main()
