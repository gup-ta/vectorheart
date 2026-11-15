"""Opt-in real provider / actual worker verification, isolated from user data.

Run: backend/.venv/Scripts/python backend/tests/live_stage3.py --verify
At most seven paid model requests; no API keys or private project data are printed.
"""
import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); parser.add_argument('--focus',choices=['all','graph','discovery'],default='all')
    args=parser.parse_args()
    if not args.verify: parser.error('Pass --verify to permit bounded paid Gemini calls.')
    from dotenv import load_dotenv
    load_dotenv(BACKEND / '.env', override=False)
    model = os.getenv('GEMINI_DEFAULT_MODEL')
    if not os.getenv('GEMINI_API_KEY') or not model: raise RuntimeError('Configure GEMINI_API_KEY and GEMINI_DEFAULT_MODEL first.')
    with tempfile.TemporaryDirectory(prefix='vectorheart-stage3-live-') as directory:
        os.environ['KERNEL_DB_PATH'] = str(Path(directory) / 'test.sqlite3')
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(BACKEND / 'alembic.ini')), 'head')
        from app.db import engine, uid
        from app.main import app
        from app import stage3
        from app.model_providers import GeminiProvider
        original_generate=GeminiProvider.generate_structured_response
        calls=[0]
        def bounded_generate(self,request):
            calls[0]+=1
            if calls[0]>7:raise RuntimeError('Live smoke-test limit of seven model calls reached.')
            return original_generate(self,request)
        GeminiProvider.generate_structured_response=bounded_generate
        from fastapi.testclient import TestClient
        # Run the same durable worker synchronously for a deterministic test boundary.
        stage3.schedule = stage3.drive
        try:
            with TestClient(app) as client:
                def post(path, body=None):
                    r = client.post('/v1/' + path, json=body or {}); assert r.status_code == 200, r.text
                    return r.json()
                def get(path):
                    r = client.get('/v1/' + path); assert r.status_code == 200, r.text
                    return r.json()
                settings = {'modelAssignments': {role: {'provider': 'Google Gemini', 'modelId': model} for role in ['General Reasoning', 'Conceptual Synthesis']}}
                p = post('projects', {'title': 'Disposable myopia journal', 'settings': settings})
                base = 'projects/' + p['id']
                post(base + '/journal', {'title': 'Day one', 'body': 'Illustrative research diary, not a clinical finding: I suspect the reported screen-time association with myopia may reflect reduced outdoor light rather than screen exposure itself. Our observations cannot yet distinguish these explanations. This is a tentative hypothesis, not verified evidence.'})
                post(base + '/journal', {'title': 'Day two', 'body': 'The PI suggested books could involve similar near-work exposure. I wonder whether near-work confounds the association between outdoor time and myopia. We have not performed a clinical experiment. The current records show only a reported correlation; causal direction remains an open question.'})
                def run(base, kind, objective='', max_steps=3):
                    r = post(base + '/research-runs', {'kind': kind, 'objective': objective, 'max_steps': max_steps, 'idempotency_key': uid()})
                    r = get(base + '/research-runs/' + r['id'])
                    if r['status'] == 'failed' and r.get('error') and ('overloaded' in r['error'] or 'timed out' in r['error']):
                        print('LIVE external availability failure; one explicit checkpoint retry.', flush=True)
                        time.sleep(3)
                        post(base + '/research-runs/' + r['id'] + '/resume')
                        r = get(base + '/research-runs/' + r['id'])
                    assert r['status'] not in ['failed', 'interrupted'], r.get('error')
                    print('LIVE', kind, r['status'], 'model=', model, 'requests=', r['model_requests'], flush=True)
                    return r
                if args.focus in ['all','graph']:
                    graph = run(base, 'graph'); assert graph['status'] == 'review'
                    assert graph['output']['nodes'] and graph['output']['edges'], graph['output'].get('diagnostics')
                    post(base + '/research-runs/' + graph['id'] + '/accept-graph')
                    nodes = get(base + '/objects')
                    assert any(o['metadata'].get('source_passages') for o in nodes)
                    edges = get(base + '/relationships')
                    edge = next((e for e in edges if e['relationship_type'] != 'derived_from'), edges[0])
                    post(base + '/graph/corrections', {'kind': 'remove_relationship', 'relationship_id': edge['id'], 'rationale': 'The record establishes a reported correlation, not a causal explanation.'})
                    update = run(base, 'graph'); post(base + '/research-runs/' + update['id'] + '/accept-graph')
                    assert not any(e['source_object_id'] == edge['source_object_id'] and e['target_object_id'] == edge['target_object_id'] and e['relationship_type'] == edge['relationship_type'] for e in get(base + '/relationships'))
                    print('VERIFIED journal graph, source provenance, correction and incremental rejection protection.', flush=True)
                if args.focus=='graph':return
                accelerate = run(base, 'accelerate', 'Propose one novel, testable hypothesis beyond these recorded explanations. Return a structured create_hypothesis proposal, not clinical results.')
                proposals = get(base + '/research-runs/' + accelerate['id'] + '/proposals')
                hypothesis = next(p for p in proposals if p['action_type'] == 'create_hypothesis')
                path = base + '/research-runs/' + accelerate['id'] + '/proposals/' + hypothesis['id'] + '/accept'
                accepted = post(path); assert post(path)['result_ids'] == accepted['result_ids']
                obj = get(base + '/objects/' + accepted['result_ids']['object_id'])
                assert obj['metadata']['origin'] == 'ai_accelerate'
                assert any(v['objectId'] == obj['id'] for v in get(base)['placements'])
                print('VERIFIED real novel Gemini hypothesis, human acceptance, shared Canvas identity and idempotency.', flush=True)
                p2 = post('projects', {'title': 'Disposable synthetic investigation', 'settings': settings}); causal = 'projects/' + p2['id']; post(causal + '/demo')
                agent = run(causal, 'investigate', 'Perform exactly one registered synthetic causal intervention to distinguish Model A from Model B: world A, do(X=2), 1000 samples, seed 42. First propose the executable experiment. After real evidence arrives, do not propose a second experiment; propose a scientifically cautious revision scoped to this simulation, citing its actual evidence object.', max_steps=3)
                assert agent['status'] == 'awaiting_approval', agent['output']
                opid = agent['steps'][-1]['operation_id']
                assert get(causal + '/operations/' + opid)['status'] == 'draft'
                assert get(causal + '/runs') == []
                post(causal + '/research-runs/' + agent['id'] + '/approve')
                finished = get(causal + '/research-runs/' + agent['id'])
                assert finished['status'] == 'completed', finished.get('error')
                assert finished['tool_executions'] == 1
                measured = get(causal + '/runs')[0]
                assert measured['status'] == 'completed' and len(measured['measured_outputs']['samples']) == 1000
                proposals = get(causal + '/research-runs/' + agent['id'] + '/proposals')
                revisions = [p for p in proposals if p['action_type'] == 'propose_revision']
                assert revisions, finished['output']
                accepted = post(causal + '/research-runs/' + agent['id'] + '/proposals/' + revisions[0]['id'] + '/accept')
                assert len(get(causal + '/objects/' + accepted['result_ids']['object_id'] + '/revisions')) >= 2
                assert any(e['event_type'] == 'investigation_evidence_received' for e in get(causal + '/events'))
                print('VERIFIED model-selected tool, draft approval pause, actual NumPy measurements, evidence-grounded follow-up and accepted revision.', flush=True)
                print('ALL LIVE STAGE 3 CHECKS PASSED. Disposable database only.', flush=True)
        finally:
            stage3.pool.shutdown(wait=True)
            engine.dispose()


if __name__ == '__main__': main()
