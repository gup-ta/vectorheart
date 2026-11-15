"""Explicit live scholarly/model smoke tests; disposable DB, no browser, no fake responses.

--retrieval-only uses public APIs only. --verify additionally permits at most seven
configured Gemini calls. All clinical interpretation is population-level research.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--retrieval-only',action='store_true');parser.add_argument('--verify',action='store_true');parser.add_argument('--tools',action='store_true');parser.add_argument('--focus',choices=['all','intelligence','agent'],default='all');args=parser.parse_args()
    if not(args.retrieval_only or args.verify):parser.error('Explicitly choose --retrieval-only or --verify.')
    from dotenv import load_dotenv
    load_dotenv(BACKEND/'.env',override=False)
    with tempfile.TemporaryDirectory(prefix='vectorheart-literature-live-') as directory:
        os.environ['KERNEL_DB_PATH']=str(Path(directory)/'test.sqlite3')
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(BACKEND/'alembic.ini')),'head')
        from app.db import engine,uid,Session
        from app.main import app
        from app import stage3
        from app.model_providers import GeminiProvider
        from fastapi.testclient import TestClient
        stage3.schedule=stage3.drive
        calls=[0];original=GeminiProvider.generate_structured_response
        def bounded(self,request):
            calls[0]+=1
            if calls[0]>7:raise RuntimeError('Live test limit of seven model requests reached.')
            result=original(self,request)
            if hasattr(result.output,'context_references'):
                objects={v['id'] for v in request.context.get('objects',[])};sources={v['source_id'] for v in request.context.get('literature',[])};snapshots={v['snapshot_id'] for v in request.context.get('literature',[])}
                print('LIVE literature reference roles:',[('source' if v in sources else 'snapshot' if v in snapshots else 'other') for v in result.output.literature_references],flush=True)
                print('LIVE citation roles:',[('object' if v in objects else 'source' if v in sources else 'snapshot' if v in snapshots else 'unknown') for v in result.output.context_references],flush=True)
            return result
        GeminiProvider.generate_structured_response=bounded
        try:
            with TestClient(app) as client:
                def post(path,data=None):
                    r=client.post('/v1/'+path,json=data or {});assert r.status_code==200,r.text;return r.json()
                def get(path):
                    r=client.get('/v1/'+path);assert r.status_code==200,r.text;return r.json()
                model=os.getenv('GEMINI_DEFAULT_MODEL')
                settings={'modelAssignments':{role:{'provider':'Google Gemini','modelId':model or ''} for role in ['General Reasoning','Literature Analysis','Conceptual Synthesis']}}
                pid=post('projects',{'title':'Disposable literature research','description':'Synthetic hypothesis for software verification; not individual medical advice.','settings':settings})['id'];base='projects/'+pid
                h=post(base+'/objects',{'projectId':pid,'type':'Hypothesis','title':'Outdoor light and childhood myopia','body':'Outdoor light exposure may contribute to differences in childhood myopia risk independently of time spent using digital screens.'})
                def search(action,use_model):
                    r=post(base+'/literature/runs',{'action':action,'object_ids':[h['id']],'query':'myopia outdoor light children','use_model':use_model,'idempotency_key':uid()})
                    return get(base+'/research-runs/'+r['id'])
                raw=search('ground',False);sources=get(base+'/literature/sources?run_id='+raw['id']);assert sources
                print('LIVE scholarly retrieval:',raw['status'],raw['output']['retrieval'],flush=True)
                for p in sources[:3]:print('VERIFIED PUBLIC SOURCE',p['title'],p['identifiers'],'access=',p['access_level'],flush=True)
                sid=sources[0]['source_id'];paper=post(base+'/literature/sources/'+sid+'/save')
                assert post(base+'/literature/sources/'+sid+'/save')['id']==paper['id']
                assert any(o['id']==paper['id'] for o in get(base)['objects'])
                assert any(p['objectId']==paper['id'] for p in get(base)['placements'])
                invalid=client.post('/v1/'+base+'/literature/resolve',json={'identifier':'10.9999/vectorheart-nonexistent-reference-987654321'})
                assert invalid.status_code in [404,422],invalid.text
                print('VERIFIED invalid DOI safely rejected:',invalid.status_code,flush=True)
                if args.tools:
                    from app.literature import execute_tool
                    inspected=execute_tool(pid,raw['id'],{'tool':'literature.inspect_source','query':None,'identifier':None,'source_id':sid,'rationale':'Inspect a verified returned source.'})
                    assert inspected['sources'][0]['source_id']==sid
                    related=execute_tool(pid,raw['id'],{'tool':'literature.find_related','query':None,'identifier':None,'source_id':sid,'rationale':'Inspect actual reference-list neighbors; not an agreement claim.'})
                    assert related['sources'],related.get('warnings')
                    print('VERIFIED registered source-inspection and related/reference discovery:',len(related['sources']),'actual records;',related['relationship_notice'],flush=True)
                if not args.verify:return
                if not model or not os.getenv('GEMINI_API_KEY'):raise RuntimeError('Set GEMINI_API_KEY and GEMINI_DEFAULT_MODEL to run the opt-in live model checks.')
                if args.focus!='agent':
                    ground=search('ground',True) if args.focus=='all' else get(base+'/research-runs/'+post(base+'/literature/runs/'+raw['id']+'/analyze')['id'])
                    print('LIVE Gemini literature analysis:',model,ground['status'],ground.get('error'),flush=True)
                    assert ground['status']=='completed',ground.get('error')
                    proposals=get(base+'/research-runs/'+ground['id']+'/proposals');assert proposals,ground['output']
                    accepted=post(base+'/intelligence/proposals/'+proposals[0]['id']+'/accept')
                    assert post(base+'/intelligence/proposals/'+proposals[0]['id']+'/accept')['result_ids']==accepted['result_ids']
                    assert any(r['id']==accepted['result_ids']['relationship_id'] for r in get(base+'/relationships'))
                    assert get(base+'/objects/'+accepted['result_ids']['object_id']+'/revisions')
                    print('VERIFIED literature interpretation accepted, genuine shared paper/claim/relationship records and provenance persisted.',flush=True)
                    if args.focus=='all':
                        challenge=search('challenge',True);assert challenge['status']=='completed',challenge.get('error')
                        print('VERIFIED adversarial queries:',challenge['output']['queries'],'summary:',challenge['output']['summary'][:600],flush=True)
                    a=post(base+'/research-runs',{'kind':'accelerate','objective':'Use the retrieved literature to propose one new testable boundary-condition hypothesis beyond the existing claim. Cite actual literature source IDs. Do not merely repeat a source abstract.','max_steps':3,'idempotency_key':uid()})
                    a=get(base+'/research-runs/'+a['id']);assert a['status']=='completed',a.get('error')
                    ps=get(base+'/research-runs/'+a['id']+'/proposals');p=next(p for p in ps if p['payload'].get('literature_source_ids'))
                    accepted=post(base+'/intelligence/proposals/'+p['id']+'/accept');assert accepted['result_ids']
                    print('VERIFIED literature-aware Accelerate proposal and human acceptance.',flush=True)
                p2=post('projects',{'title':'Disposable agentic literature research','settings':settings})['id'];b2='projects/'+p2
                post(b2+'/objects',{'projectId':p2,'type':'Hypothesis','title':'Outdoor light versus near-work','body':'Outdoor light may affect myopia risk separately from near-work; current synthetic notes do not distinguish mechanisms.'})
                agent=post(b2+'/research-runs',{'kind':'investigate','objective':'First use literature.search with query myopia outdoor light children. After real sources return, inspect the supplied abstracts and propose one literature-informed hypothesis or question citing those actual sources. Do not run the toy causal simulator or pretend to execute clinical research.','max_steps':3,'idempotency_key':uid()})
                done=get(b2+'/research-runs/'+agent['id']);assert done['status']=='completed',done.get('error')
                tools=[s for s in done['steps'] if s['kind']=='literature_tool'];assert tools and tools[0]['result']['sources']
                assert done['steps_used']>=2 and done['tool_executions']>=1
                assert get(b2+'/runs')==[]
                print('VERIFIED real agent-selected scholarly tool, actual returned records, evidence-grounded follow-up and persistent bounded trace.',flush=True)
                print('ALL REQUESTED LIVE STAGE 4 CHECKS PASSED; focus:',args.focus,'model calls:',calls[0],flush=True)
        finally:
            stage3.pool.shutdown(wait=True);engine.dispose()


if __name__=='__main__':main()
