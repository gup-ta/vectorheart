"""Real kernel persistence and computation; deterministic inference never costs credits."""
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app import stage3, intelligence
from app.db import Session, Object, Operation, uid
from app.stage3_models import ResearchRun
from app.stage3_schemas import GraphExtraction
from app.intelligence_schemas import ResearchIntelligenceResponse
from app.model_providers import ModelResponse, ProviderError

client = TestClient(app)


def post(path, data=None):
    r = client.post('/v1/' + path, json=data or {})
    assert r.status_code == 200, r.text
    return r.json()


def get(path):
    r = client.get('/v1/' + path); assert r.status_code == 200, r.text
    return r.json()


def project():
    p = post('projects', {'title': 'Disposable Stage 3 research'})
    return p['id'], f"projects/{p['id']}"


def proposal(action, **patch):
    return {'action_type': action, 'title': 'A discriminating prediction', 'content': 'The claim remains scoped to the synthetic intervention, not external reality.', 'rationale': 'Compare independently generated measurements against competing predictions.', 'assumptions': ['Synthetic model definitions'], 'predictions': ['An intervened difference in mean'], 'limitations': ['Simulation only'], 'referenced_object_ids': [], 'target_object_id': None, 'adapter_id': None, 'adapter_parameters': None, 'evidence_ids': [], **patch}


class Provider:
    calls = []
    def generate_structured_response(self, request):
        self.calls.append(request)
        if request.schema is GraphExtraction:
            passages = request.context['passages']; src = passages[0]
            source = {'object_id': src['id'], 'revision': src['revision'], 'excerpt': src['body'][:80]}
            return ModelResponse(GraphExtraction.model_validate({'summary': 'The records distinguish correlation from a proposed mechanism.', 'nodes': [
                {'key': 'h', 'existing_object_id': None, 'object_type': 'hypothesis', 'title': 'Outdoor light mechanism', 'body': 'Outdoor light could explain the reported association.', 'rationale': 'Explicitly suspected in the journal.', 'uncertainty': 'inferred', 'sources': [source]},
                {'key': 'q', 'existing_object_id': None, 'object_type': 'question', 'title': 'Near-work confounding', 'body': 'Could near-work account for the association?', 'rationale': 'An unresolved alternative in the journal.', 'uncertainty': 'explicit', 'sources': [source]}],
                'edges': [{'source': 'h', 'target': 'q', 'relationship_type': 'related_to', 'rationale': 'Alternative explanations for an unverified association.', 'uncertainty': 'uncertain', 'sources': [source]}], 'limitations': ['No clinical measurements were executed.']}))
        ctx = request.context
        causal = next((o for o in ctx['objects'] if o.get('metadata', {}).get('causal_demo') and o['object_type'] == 'hypothesis'), None)
        if causal and not ctx['evidence']:
            p = proposal('propose_experiment', target_object_id=causal['id'], referenced_object_ids=[causal['id']], adapter_id='toy.causal_intervention.v1', adapter_parameters={'data_generating_world': 'A', 'intervention_value': 2, 'sample_count': 1000, 'seed': 42})
        elif causal:
            evidence = ctx['evidence'][0]
            assert evidence['measured_results']['mean'] != 0
            p = proposal('propose_revision', target_object_id=causal['id'], evidence_ids=[evidence['object_id']], referenced_object_ids=[causal['id'], evidence['object_id']])
        else:
            p = proposal('create_hypothesis', title='A novel interaction hypothesis', content='Outdoor light modifies the association between near-work and myopia.', referenced_object_ids=[ctx['objects'][0]['id']])
        return ModelResponse(ResearchIntelligenceResponse(answer='Actual recorded evidence informs this next action.' if ctx['evidence'] else 'A testable next action.', uncertainties=['Scope remains limited.'], context_references=p['referenced_object_ids'], proposals=[p], limitations=['Not real-world proof.']), {'total_tokens': 100})


@pytest.fixture
def provider(monkeypatch):
    value = Provider(); value.calls = []
    monkeypatch.setattr(stage3, 'route', lambda *a: ('Google Gemini', 'test-stage3', value))
    monkeypatch.setattr(intelligence, 'route', lambda *a: ('Google Gemini', 'test-stage3', value))
    monkeypatch.setattr(stage3, 'schedule', stage3.drive)
    return value


def run(base, kind='graph', **patch):
    r = post(base + '/research-runs', {'kind': kind, 'objective': 'Distinguish competing explanations.', 'idempotency_key': uid(), **patch})
    return get(base + '/research-runs/' + r['id'])


def test_journal_revisions_tags_links_and_stale_drafts():
    pid, base = project()
    entry = post(base + '/journal', {'title': 'Day one', 'body': 'Original free-form writing.', 'tags': ['causality']})
    assert entry['type'] == 'Note' and entry['metadata']['journal_entry']
    body = {'title': 'Day one', 'body': 'A revised thought.', 'base_revision': 1, 'tags': ['causality'], 'linked_object_ids': []}
    assert client.patch('/v1/' + base + '/journal/' + entry['id'], json=body).json()['currentRevision'] == 2
    assert client.patch('/v1/' + base + '/journal/' + entry['id'], json=body).status_code == 409
    assert get(base + '/journal')[0]['body'] == 'A revised thought.'
    revisions = get(base + '/objects/' + entry['id'] + '/revisions')
    assert revisions[0]['body_snapshot'] == 'Original free-form writing.'
    other, _ = project()
    assert client.get(f"/v1/projects/{other}/objects/{entry['id']}").status_code == 404
    assert client.post('/v1/' + base + '/journal', json={'linked_object_ids': ['missing']}).status_code == 404


def test_graph_preview_accept_incremental_identity_and_rejected_relationship(provider):
    pid, base = project()
    entry = post(base + '/journal', {'title': 'Observational uncertainty', 'body': 'Outdoor light might explain myopia associations. Near-work could confound the reported correlation.'})
    preview = run(base); assert preview['status'] == 'review', preview
    assert len(get(base + '/objects')) == 1  # No scientific mutation during inference.
    accepted = post(base + '/research-runs/' + preview['id'] + '/accept-graph')
    assert accepted['status'] == 'accepted'
    assert post(base + '/research-runs/' + preview['id'] + '/accept-graph')['status'] == 'accepted'
    objects = get(base + '/objects'); assert len(objects) == 3
    assert get(base + '/journal')[0]['body'] == entry['body']
    extracted = next(o for o in objects if o['title'] == 'Outdoor light mechanism')
    assert extracted['metadata']['source_passages'][0]['revision'] == 1
    edge = next(e for e in get(base + '/relationships') if e['relationship_type'] == 'related_to')
    post(base + '/graph/corrections', {'kind': 'remove_relationship', 'relationship_id': edge['id'], 'rationale': 'Only correlation was reported, not a causal relationship.'})
    again = run(base)
    assert any('rejected' in v for v in again['output']['diagnostics'])
    post(base + '/research-runs/' + again['id'] + '/accept-graph')
    assert len(get(base + '/objects')) == 3
    assert not any(e['relationship_type'] == 'related_to' for e in get(base + '/relationships'))
    assert get(base + '/graph/corrections')[0]['before']['id'] == edge['id']
    assert provider.calls[-1].context['corrections'][0]['rationale'].startswith('Only correlation')
    assert len(get(base + '/canvas')) == 2


def test_graph_source_revision_conflict_and_researcher_type_correction(provider):
    _, base = project()
    journal = post(base + '/journal', {'body': 'The relationship may be confounded by near-work.'})
    preview = run(base)
    client.patch('/v1/' + base + '/journal/' + journal['id'], json={'body': 'Changed source.', 'base_revision': 1})
    assert client.post('/v1/' + base + '/research-runs/' + preview['id'] + '/accept-graph').status_code == 409
    preview = run(base); post(base + '/research-runs/' + preview['id'] + '/accept-graph')
    obj = next(o for o in get(base + '/objects') if o['type'] == 'Hypothesis')
    post(base + '/graph/corrections', {'kind': 'edit_object', 'object_id': obj['id'], 'base_revision': obj['currentRevision'], 'object_type': 'question', 'rationale': 'This was a question, not my claim.'})
    assert get(base + '/objects/' + obj['id'])['type'] == 'Question'
    assert len(get(base + '/objects/' + obj['id'] + '/revisions')) == 2
    next_run = run(base); post(base + '/research-runs/' + next_run['id'] + '/accept-graph')
    assert get(base + '/objects/' + obj['id'])['type'] == 'Question'
    assert len(get(base + '/objects')) == 3


def test_large_journal_is_processed_at_every_span_without_recent_only_truncation(provider):
    _, base = project()
    post(base + '/journal', {'body': 'Repeated observations and uncertainties. ' * 700})
    result = run(base)
    assert result['config']['chunk_count'] > 1
    assert result['model_requests'] == result['config']['chunk_count']
    passages = [p for request in provider.calls for p in request.context['passages']]
    assert [p['span_start'] for p in passages] == list(range(0, len('Repeated observations and uncertainties. ' * 700), 6000))
    post(base+'/research-runs/'+result['id']+'/accept-graph')
    accelerated=run(base,'accelerate')
    assert accelerated['status']=='completed',accelerated


def test_accelerate_is_reviewable_shared_and_idempotent(provider):
    _, base = project()
    source = post(base + '/journal', {'body': 'Outdoor light and near-work may interact.'})
    result = run(base, 'accelerate'); assert result['status'] == 'completed', result
    proposal = get(base + '/research-runs/' + result['id'] + '/proposals')[0]
    assert proposal['status'] == 'pending' and len(get(base + '/objects')) == 1
    path = base + '/research-runs/' + result['id'] + '/proposals/' + proposal['id'] + '/accept'
    accepted = post(path); again = post(path)
    assert accepted['result_ids'] == again['result_ids']
    oid = accepted['result_ids']['object_id']
    loaded = get(base); assert len(loaded['objects']) == 2
    obj = next(o for o in loaded['objects'] if o['id'] == oid)
    assert obj['metadata']['origin'] == 'ai_accelerate'
    assert any(p['objectId'] == oid for p in loaded['placements'])
    assert get(base + '/objects/' + source['id'])['body'] == source['body']


def test_bounded_agent_pauses_approves_executes_real_numpy_then_uses_evidence(provider):
    _, base = project(); post(base + '/demo')
    result = run(base, 'investigate'); assert result['status'] == 'awaiting_approval', result
    opid = result['steps'][0]['operation_id']; assert get(base + '/operations/' + opid)['status'] == 'draft'
    assert client.post('/v1/' + base + '/operations/' + opid + '/execute').status_code == 409
    assert get(base + '/runs') == []
    post(base + '/research-runs/' + result['id'] + '/approve')
    done = get(base + '/research-runs/' + result['id']); assert done['status'] == 'completed', done
    assert done['tool_executions'] == 1 and done['steps_used'] == 2
    measured = get(base + '/runs')[0]; assert measured['status'] == 'completed'
    assert len(measured['measured_outputs']['samples']) == 1000
    assert get(base + '/evidence')[0]['verification_status'] == 'execution_checked'
    assert provider.calls[-1].context['evidence'][0]['measured_results']['mean'] == measured['measured_outputs']['mean']
    revision = next(p for p in get(base + '/research-runs/' + result['id'] + '/proposals') if p['action_type'] == 'propose_revision')
    post(base + '/research-runs/' + result['id'] + '/proposals/' + revision['id'] + '/accept')
    assert len(get(base + '/objects/' + revision['payload']['target_object_id'] + '/revisions')) >= 2
    post(base + '/research-runs/' + result['id'] + '/resume')
    assert len(get(base + '/runs')) == 1
    assert any(e['event_type'] == 'investigation_evidence_received' for e in get(base + '/events'))


def test_prepared_experiment_generic_accept_does_not_duplicate_operation(provider):
    _, base = project(); post(base + '/demo'); r = run(base, 'investigate')
    p = get(base + '/research-runs/' + r['id'] + '/proposals')[0]
    count = len(get(base + '/operations'))
    accepted = post(base + '/intelligence/proposals/' + p['id'] + '/accept')
    assert accepted['result_ids']['operation_id'] == r['steps'][0]['operation_id']
    assert len(get(base + '/operations')) == count


def test_rejected_operation_stops_without_fake_evidence(provider):
    _, base = project(); post(base + '/demo'); r = run(base, 'investigate')
    post(base + '/operations/' + r['steps'][0]['operation_id'] + '/reject')
    post(base + '/research-runs/' + r['id'] + '/resume')
    assert get(base + '/research-runs/' + r['id'])['status'] == 'completed'
    assert get(base + '/evidence') == [] and get(base + '/runs') == []


def test_limits_failures_cross_project_and_cancel(provider, monkeypatch):
    pid, base = project(); post(base + '/demo')
    r = run(base, 'investigate', max_steps=1)
    assert r['steps_used'] == 1 and r['tool_executions'] == 0 and r['status'] == 'completed'
    pid2, base2 = project()
    assert client.get('/v1/' + base2 + '/research-runs/' + r['id']).status_code == 404
    class Failure:
        def generate_structured_response(self, request): raise ProviderError('model_unavailable', 'Provider unavailable; retry later.')
    monkeypatch.setattr(stage3, 'route', lambda *a: ('Google Gemini', 'test', Failure()))
    failed = run(base); assert failed['status'] == 'failed' and failed['model_requests'] == 1
    post(base + '/research-runs/' + failed['id'] + '/cancel')
    post(base + '/research-runs/' + failed['id'] + '/resume')
    assert get(base + '/research-runs/' + failed['id'])['status'] == 'cancelled'


def test_invalid_excerpts_and_references_are_not_accepted():
    source = {'id': 'source', 'revision': 1, 'body': 'Only correlation was observed.', 'title': 'Record', 'type': 'note', 'metadata': {}}
    snapshot = {'records': [source], 'corrections': []}
    with pytest.raises(ValueError, match='exactly'):
        stage3.source_grounding([type('Source', (), {'object_id': 'source', 'revision': 1, 'excerpt': 'Invented observation'})()], snapshot)
    with pytest.raises(ValueError, match='outside'):
        stage3.source_grounding([type('Source', (), {'object_id': 'foreign', 'revision': 1})()], snapshot)


def test_lease_prevents_parallel_resume_and_survives_session_reload(provider, monkeypatch):
    _, base = project(); post(base + '/journal', {'body': 'An uncertainty.'})
    monkeypatch.setattr(stage3, 'schedule', lambda *a: None)
    data = {'kind': 'graph', 'idempotency_key': uid()}
    r = post(base + '/research-runs', data)
    assert post(base + '/research-runs', data)['id'] == r['id']
    with Session() as s:
        saved = s.get(ResearchRun, r['id']); assert saved.snapshot['records'][0]['body'] == 'An uncertainty.'
    stage3.drive(r['project_id'], r['id'])
    completed = get(base + '/research-runs/' + r['id'])
    assert completed['status'] == 'review' and completed['lease_until'] is None
    before = len(provider.calls); stage3.drive(r['project_id'], r['id'])
    assert len(provider.calls) == before


def test_approval_checkpoint_resumes_in_fresh_python_process(provider):
    """The second process uses durable SQLite state, not the first worker's memory."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    _, base = project(); post(base + '/demo'); r = run(base, 'investigate')
    post(base + '/operations/' + r['steps'][0]['operation_id'] + '/approve')
    source = '''import sys
sys.path[:0]=['backend','backend/tests']
from test_stage3 import Provider
from app import stage3,intelligence
from app.db import engine
provider=Provider()
stage3.route=lambda *a:('Google Gemini','test-stage3',provider)
intelligence.route=stage3.route
stage3.drive(sys.argv[1],sys.argv[2])
engine.dispose()
'''
    result = subprocess.run([sys.executable, '-c', source, r['project_id'], r['id']], cwd=Path(__file__).resolve().parents[2], env=os.environ.copy(), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    restored = get(base + '/research-runs/' + r['id'])
    assert restored['status'] == 'completed' and restored['tool_executions'] == 1
    assert len(get(base + '/runs')) == 1 and get(base + '/evidence')
    stage3.drive(r['project_id'], r['id'])
    assert len(get(base + '/runs')) == 1


def test_context_corrected_relationship_is_deterministically_rejected(provider):
    _, base = project()
    a = post(base + '/objects', {'projectId': base.split('/')[1], 'type': 'Hypothesis', 'title': 'A', 'body': 'One claim.'})
    b = post(base + '/objects', {'projectId': base.split('/')[1], 'type': 'Hypothesis', 'title': 'B', 'body': 'Another claim.'})
    edge = post(base + '/graph/corrections', {'kind': 'add_relationship', 'source_id': a['id'], 'target_id': b['id'], 'rationale': 'Researcher interpretation.'})
    post(base + '/graph/corrections', {'kind': 'remove_relationship', 'relationship_id': edge['after']['id'], 'rationale': 'This inference was incorrect.'})
    with Session() as s:
        p = intelligence.ScientificProposal.model_validate(proposal('propose_relationship', source_object_id=a['id'], target_object_id=b['id'], relationship_type='related_to', referenced_object_ids=[a['id'], b['id']]))
        with pytest.raises(ValueError, match='rejected'):
            intelligence.validated_proposal(s, a['projectId'], p, {'objects': [{'id': a['id']}, {'id': b['id']}]})
    post(base + '/graph/corrections', {'kind': 'add_relationship', 'source_id': a['id'], 'target_id': b['id'], 'rationale': 'Explicit researcher reinstatement.'})
    with Session() as s: assert not stage3.relationship_blocked(s, a['projectId'], a['id'], b['id'], 'related_to')


def test_conceptual_and_invalid_tools_never_execute(provider, monkeypatch):
    pid, base = project()
    h = post(base + '/objects', {'projectId': pid, 'type': 'Hypothesis', 'title': 'Myopia hypothesis', 'body': 'Outdoor light affects myopia.'})
    class Conceptual:
        def generate_structured_response(self, request):
            p = proposal('propose_experiment', title='Prospective light exposure study', content='A conceptual controlled study with appropriate clinical oversight.', target_object_id=h['id'], referenced_object_ids=[h['id']], adapter_id='clinical.unavailable')
            return ModelResponse(ResearchIntelligenceResponse(answer='Conceptual only.', uncertainties=[], context_references=[h['id']], proposals=[p], limitations=['No clinical executor.']))
    monkeypatch.setattr(intelligence, 'route', lambda *a: ('Google Gemini', 'test', Conceptual()))
    r = run(base, 'investigate'); assert r['status'] == 'completed' and r['tool_executions'] == 0
    p = get(base + '/research-runs/' + r['id'] + '/proposals')[0]; assert not p['payload']['executable']
    accepted = post(base + '/research-runs/' + r['id'] + '/proposals/' + p['id'] + '/accept')
    assert get(base + '/objects/' + accepted['result_ids']['object_id'])['metadata']['conceptual_experiment']
    assert get(base + '/runs') == [] and get(base + '/operations') == []
    with Session() as s:
        p = intelligence.ScientificProposal.model_validate(proposal('propose_experiment', target_object_id=h['id'], adapter_id='toy.causal_intervention.v1', adapter_parameters={'data_generating_world': 'A', 'intervention_value': 99, 'sample_count': 1000, 'seed': 42}))
        with pytest.raises(ValueError, match='No parameters were changed'):
            intelligence.validated_proposal(s, pid, p, {'objects': [{'id': h['id']}]})


def test_expired_lease_model_failure_retry_consumes_budget_and_stale_accelerate_conflicts(provider, monkeypatch):
    from datetime import datetime, timedelta, timezone
    pid, base = project(); source = post(base + '/journal', {'body': 'A possible mechanism.'})
    r = run(base, 'accelerate'); p = get(base + '/research-runs/' + r['id'] + '/proposals')[0]
    client.patch('/v1/' + base + '/journal/' + source['id'], json={'body': 'A different interpretation.', 'base_revision': 1})
    assert client.post('/v1/' + base + '/research-runs/' + r['id'] + '/proposals/' + p['id'] + '/accept', json={}).status_code == 409
    monkeypatch.setattr(stage3, 'schedule', lambda *a: None)
    r = post(base + '/research-runs', {'kind': 'graph', 'idempotency_key': uid()})
    with stage3.kernel().transaction() as s:
        record = s.get(ResearchRun, r['id']); record.lease_until = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat(); record.lease_owner = 'another-worker'
    count = len(provider.calls); stage3.drive(pid, r['id']); assert len(provider.calls) == count
    with stage3.kernel().transaction() as s:
        s.get(ResearchRun, r['id']).lease_until = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    stage3.drive(pid, r['id']); assert get(base + '/research-runs/' + r['id'])['status'] == 'review'


def test_committed_inference_is_reconciled_after_worker_loss_without_new_proposals(provider, monkeypatch):
    from app.stage3_models import ResearchStep
    pid, base = project(); post(base + '/journal', {'body': 'An open question about a possible mechanism.'})
    monkeypatch.setattr(stage3, 'schedule', lambda *a: None)
    r = post(base + '/research-runs', {'kind': 'accelerate', 'idempotency_key': uid()})
    conv = post(base + '/intelligence/conversations')
    with stage3.kernel().transaction() as s:
        record = s.get(ResearchRun, r['id']); stage3.consume_model(s, record)
        st = stage3.step(s, record, 'reason', {'objective': record.objective, 'step': 1}); sid = st.id
        record.steps_used = 1
        ctx = stage3.investigation_context(s, pid, record, conv['id'])
    response = intelligence.perform_turn(pid, conv['id'], intelligence.TurnRequest(message='A scientific action', idempotency_key='stage3-' + sid), context_override=ctx, run_provenance={'research_run_id': r['id']})
    assert response['status'] == 'completed'
    count = len(provider.calls)
    stage3.drive(pid, r['id'])
    assert len(provider.calls) == count
    restored = get(base + '/research-runs/' + r['id'])
    assert restored['status'] == 'completed' and restored['model_requests'] == 1
    assert len(get(base + '/research-runs/' + r['id'] + '/proposals')) == 1


def test_interrupted_running_scientific_worker_is_never_blindly_reexecuted(provider):
    pid, base = project(); post(base + '/demo'); r = run(base, 'investigate')
    with stage3.kernel().transaction() as s:
        op = s.get(Operation, r['steps'][0]['operation_id']); op.status = 'running'
    post(base + '/research-runs/' + r['id'] + '/resume')
    restored = get(base + '/research-runs/' + r['id'])
    assert restored['status'] == 'interrupted'
    assert get(base + '/runs') == [] and get(base + '/evidence') == []


def test_buffered_correction_retries_preserve_edge_identity_without_duplicate_history():
    pid, base = project()
    a = post(base + '/objects', {'projectId':pid,'type':'Note','title':'A','body':'First record.'})
    b = post(base + '/objects', {'projectId':pid,'type':'Note','title':'B','body':'Second record.'})
    edgeid, correctionid = uid(), uid()
    data={'kind':'add_relationship','correction_id':correctionid,'relationship_id':edgeid,'source_id':a['id'],'target_id':b['id'],'rationale':'Human-reported reasoning.'}
    first=post(base+'/graph/corrections',data);again=post(base+'/graph/corrections',data)
    assert first['id']==again['id'] and first['after']['id']==edgeid
    assert len(get(base+'/graph/corrections'))==1
    changed={**data,'rationale':'Different request using same ID.'}
    assert client.post('/v1/'+base+'/graph/corrections',json=changed).status_code==409
    removal={'kind':'remove_relationship','correction_id':uid(),'relationship_id':edgeid,'rationale':'An interpretation was mistaken.'}
    post(base+'/graph/corrections',removal);post(base+'/graph/corrections',removal)
    assert get(base+'/relationships')==[] and len(get(base+'/objects'))==2
    assert len(get(base+'/graph/corrections'))==2
