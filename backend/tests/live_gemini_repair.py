"""Opt-in live diagnostics. Uses only a disposable database and synthetic research.

Run explicitly with --diagnose or --verify; never collected by pytest.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

def safe(value):
    text=str(value)
    for key in ['GEMINI_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY']:
        if os.getenv(key):text=text.replace(os.environ[key],'[redacted]')
    return text[:4000]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--diagnose',action='store_true');parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if not (args.diagnose or args.verify):parser.error('Explicit --diagnose or --verify required')
    from dotenv import load_dotenv
    load_dotenv(BACKEND/'.env',override=False)
    if not os.getenv('GEMINI_API_KEY'):raise RuntimeError('GEMINI_API_KEY is not configured')
    model='gemini-3.5-flash-lite'
    with tempfile.TemporaryDirectory(prefix='vectorheart-gemini-live-') as directory:
        os.environ['KERNEL_DB_PATH']=str(Path(directory)/'kernel.sqlite3')
        from alembic.config import Config
        from alembic import command
        command.upgrade(Config(str(BACKEND/'alembic.ini')),'head')
        from app.db import engine
        try:
            from app.intelligence_schemas import ResearchIntelligenceResponse
            if args.diagnose:
                from google import genai
                from google.genai import types
                from pydantic import BaseModel
                class SimpleResponse(BaseModel):
                    answer:str
                    hypotheses:list[str]
                with genai.Client(api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=40000,retry_options=types.HttpRetryOptions(attempts=1))) as client:
                    for name,schema in [('A minimal',SimpleResponse),('B canonical',ResearchIntelligenceResponse)]:
                        try:
                            response=client.models.generate_content(model=model,contents='Explain why rain occurs. Give a concise scientific explanation, with no proposals if unnecessary.',config=types.GenerateContentConfig(response_mime_type='application/json',response_schema=schema,max_output_tokens=3000))
                            schema.model_validate_json(response.text)
                            print(name,'SUCCESS',flush=True)
                        except Exception as exc:print(name,'FAILED',type(exc).__name__,'status=',getattr(exc,'code',None),safe(exc),flush=True)
            from fastapi.testclient import TestClient
            from app.main import app
            from app.intelligence_schemas import MODE_ROLES
            with TestClient(app) as client:
                def post(path,payload={}):
                    result=client.post('/v1/'+path,json=payload)
                    if result.status_code!=200:raise RuntimeError(safe(result.json()))
                    return result.json()
                project=post('projects',{'title':'Disposable live Gemini verification','description':'Synthetic water and plant observations, not user research.','settings':{'modelAssignments':{role:{'provider':'Google Gemini','modelId':model} for role in MODE_ROLES.values()}}})
                pid=project['id'];base=f'projects/{pid}'
                question=post(base+'/objects',{'projectId':pid,'type':'Question','title':'Water and seedlings','body':'How does water availability affect seedling growth under controlled light?'});
                observation=post(base+'/objects',{'projectId':pid,'type':'Observation','title':'Synthetic preliminary observation','body':'A hypothetical classroom report describes greater seedling growth with adequate water. This is unverified illustrative source text, not measured experimental evidence.'})
                cid=post(base+'/intelligence/conversations')['id']
                explanation=post(base+f'/intelligence/conversations/{cid}/turns',{'message':'Explain how water availability might affect seedling growth, distinguishing mechanisms from evidence. No proposal is needed for this explanation.','mode':'Explore','selected_object_id':question['id'],'idempotency_key':'live-explanation-request'})
                print('C full pathway',explanation['status'],'model=',model,'answer_chars=',len(explanation['content']),'details=',safe(explanation['response_details']),flush=True)
                if args.verify:
                    assert explanation['status']=='completed',safe(explanation['content'])
                    hypothesis=post(base+f'/intelligence/conversations/{cid}/turns',{'message':'Propose exactly one new testable hypothesis about water availability and seedling growth using the supplied question and synthetic observation. Return one create_hypothesis proposal with all required fields, reference the actual supplied object IDs, distinguish the unverified observation from evidence, and invent no measurements. Use null for target_object_id, adapter_id and adapter_parameters, and an empty evidence_ids array.','mode':'Formalize','selected_object_id':question['id'],'idempotency_key':'live-hypothesis-request'})
                    assert hypothesis['status']=='completed',safe(hypothesis['content'])
                    proposals=[p for p in hypothesis['proposals'] if p['action_type']=='create_hypothesis']
                    assert proposals,safe(hypothesis['response_details'])
                    accepted=post(base+f"/intelligence/proposals/{proposals[0]['id']}/accept")
                    duplicate=post(base+f"/intelligence/proposals/{proposals[0]['id']}/accept")
                    assert accepted['result_ids']==duplicate['result_ids']
                    loaded=client.get('/v1/'+base).json();oid=accepted['result_ids']['object_id'];obj=next(o for o in loaded['objects'] if o['id']==oid)
                    assert obj['type']=='Hypothesis' and obj['metadata']['model_provenance']['model']==model
                    assert sum(o['id']==oid for o in loaded['objects'])==1
                    assert client.get('/v1/'+base+'/objects/'+oid).json()['id']==oid
                    assert len(loaded['objects'])==3
                    assert obj['id'] not in [question['id'],observation['id']]
                    # Shared project objects are the Notebook/Canvas source; place the exact accepted object.
                    assert client.put('/v1/'+base+'/canvas/'+oid,json={'x':20,'y':40}).status_code==200
                    assert any(p['object_id']==oid for p in client.get('/v1/'+base+'/canvas').json())
                    print('HYPOTHESIS',json.dumps({'status':accepted['status'],'canonical_valid':True,'type':obj['type'],'title':obj['title'],'statement':obj['body'],'provenance_model':obj['metadata']['model_provenance']['model'],'notebook_retrieval':True,'canvas_shared_object':True,'idempotent_acceptance':True}),flush=True)
        finally:engine.dispose()
    print('Disposable database removed; existing projects untouched.',flush=True)
if __name__=='__main__':main()
