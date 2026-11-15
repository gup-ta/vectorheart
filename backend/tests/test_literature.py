"""Real application logic using recorded CC-BY scholarly metadata and deterministic inference."""
import copy
import json
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app import literature as lit, stage3, intelligence, scholarly_providers as sp
from app.db import Session, Object, uid, now
from app.literature_models import ScholarlySource, SourceSnapshot, SourceIdentifier, LiteratureHit
from app.literature_schemas import SearchPlan, LiteratureAnalysis
from app.intelligence_schemas import ResearchIntelligenceResponse
from app.model_providers import ModelResponse, ProviderError

FIXTURE=json.loads((Path(__file__).parent/'fixtures/literature.json').read_text(encoding='utf-8'))
client=TestClient(app)
def post(path,data=None):
    r=client.post('/v1/'+path,json=data or {});assert r.status_code==200,r.text;return r.json()
def get(path):
    r=client.get('/v1/'+path);assert r.status_code==200,r.text;return r.json()
def project():
    p=post('projects',{'title':'Disposable literature research'})
    base='projects/'+p['id']
    h=post(base+'/objects',{'projectId':p['id'],'type':'Hypothesis','title':'Outdoor light and myopia','body':'Outdoor light may affect childhood myopia independently of screen time.'})
    return p['id'],base,h


class FixtureScholar:
    def __init__(self,name):self.name=name
    def paper(self):return {'OpenAlex':sp.normalize_openalex,'Europe PMC':sp.normalize_pmc,'Crossref':sp.normalize_crossref}[self.name](copy.deepcopy(FIXTURE[{'OpenAlex':'openalex','Europe PMC':'pmc','Crossref':'crossref'}[self.name]]))
    def search(self,query,budget):return [self.paper()]
    def resolve(self,kind,value,budget):
        p=self.paper()
        if p.identifiers.get(kind)!=value:raise sp.ScholarlyError(self.name,'not_found','No publication was returned for this identifier.')
        return p


def scientific_proposal(target,source_id=None):
    return {'action_type':'create_hypothesis','title':'A literature-informed boundary condition','content':'The acceptability of bright indoor light may constrain designs testing light exposure.', 'rationale':'The retrieved feasibility study motivates a testable boundary condition, not a proven myopia intervention.', 'assumptions':[], 'predictions':[], 'limitations':['Not identified across all literature; bounded retrieval only.'], 'referenced_object_ids':[target], 'target_object_id':None,'adapter_id':None,'adapter_parameters':None,'evidence_ids':[], 'literature_source_ids':[source_id] if source_id else []}


class FixtureModel:
    def __init__(self):self.calls=[]
    def generate_structured_response(self,request):
        self.calls.append(request)
        if request.schema is SearchPlan:
            action=request.context.get('project',{});challenge='challenge' in request.message
            return ModelResponse(SearchPlan(queries=[{'strategy':'alternative' if challenge else 'methodological','query':'myopia outdoor bright classroom feasibility','rationale':'Compare exposure feasibility with causal clinical efficacy.'}],limitations=['Bounded discovery.']))
        if request.schema is LiteratureAnalysis:
            source=request.context['sources'][0];target=request.context['research_objects'][0]['id']
            anchor=source['abstract'].split('. ')[0]+'.'
            return ModelResponse(LiteratureAnalysis(summary='This feasibility study does not establish a reduction in myopia onset.',findings=[{'snapshot_id':source['snapshot_id'],'target_object_id':target,'classification':'qualifies','claim':'The study assessed classroom light characteristics and user acceptability.','rationale':'Feasibility and acceptability differ from a demonstrated myopia-prevention effect.','passage':anchor,'limitations':['Abstract-only assessment.'],'method_notes':['Light measurements and user questionnaires.'],'missing_information':['A clinical effect on myopia incidence is not established here.']}],disagreements=['No genuine contradiction was established from this source.'],limitations=['Not an independently reproduced experiment.']))
        context=request.context;target=context['objects'][0]['id']
        if not context.get('literature'):
            output=ResearchIntelligenceResponse(answer='Find accessible evidence before proposing a clinical mechanism.',uncertainties=[],context_references=[target],proposals=[],limitations=[],tool_request={'tool':'literature.search','query':'myopia bright classroom outdoor light','identifier':None,'source_id':None,'rationale':'A feasibility study could inform a better experimental design.'})
        else:
            source=context['literature'][0]
            assert source['abstract'] and source['access_level']=='abstract'
            output=ResearchIntelligenceResponse(answer='Actual retrieved evidence concerns feasibility rather than clinical efficacy.',uncertainties=['Clinical effect not established.'],context_references=[target],proposals=[scientific_proposal(target,source['source_id'])],limitations=['Literature report, not local experiment.'])
        return ModelResponse(output,{'total_tokens':100})


@pytest.fixture
def setup(monkeypatch):
    model=FixtureModel()
    monkeypatch.setattr(lit,'PROVIDERS',{name:FixtureScholar(name) for name in ['OpenAlex','Europe PMC','Crossref']})
    monkeypatch.setattr(lit,'route',lambda *a:('Google Gemini','fixture-only',model))
    monkeypatch.setattr(intelligence,'route',lambda *a:('Google Gemini','fixture-only',model))
    monkeypatch.setattr(stage3,'route',lambda *a:('Google Gemini','fixture-only',model))
    monkeypatch.setattr(stage3,'schedule',stage3.drive)
    return model


def search(base,h,use_model=True,action='ground'):
    r=post(base+'/literature/runs',{'action':action,'object_ids':[h['id']],'query':'myopia outdoor light','use_model':use_model,'idempotency_key':uid()})
    return get(base+'/research-runs/'+r['id'])


def test_provider_normalization_preserves_real_identity_and_access_level():
    a=sp.normalize_openalex(FIXTURE['openalex']);p=sp.normalize_pmc(FIXTURE['pmc']);c=sp.normalize_crossref(FIXTURE['crossref'])
    assert a.identifiers['doi']==p.identifiers['doi']==c.identifiers['doi']=='10.1371/journal.pone.0181772'
    assert a.year==p.year==c.year==2017 and p.abstract and a.abstract
    assert p.access_level=='abstract' and a.retraction_status=='not_flagged'
    assert '230' in p.abstract and p.provider=='Europe PMC'
    raw={**FIXTURE['openalex'],'abstract_inverted_index':None}
    assert sp.normalize_openalex(raw).access_level=='metadata'
    with pytest.raises(ValueError):sp.doi('https://127.0.0.1/internal')
    assert sp.safe_link('http://127.0.0.1/admin') is None
    assert sp.safe_link('javascript:alert(1)') is None


def test_identifier_dedup_and_immutable_snapshot_history():
    with stage3.kernel().transaction() as s:
        a,sa=lit.persist_paper(s,sp.normalize_openalex(FIXTURE['openalex']))
        b,sb=lit.persist_paper(s,sp.normalize_pmc(FIXTURE['pmc']))
        c,sc=lit.persist_paper(s,sp.normalize_crossref(FIXTURE['crossref']))
        assert a.id==b.id==c.id and len({sa.id,sb.id,sc.id})==3
        raw=copy.deepcopy(FIXTURE['pmc']);raw['abstractText']+=' Metadata updated by provider.'
        _,new=lit.persist_paper(s,sp.normalize_pmc(raw))
        assert new.id!=sb.id and 'updated' not in sb.record['abstract']


def test_http_cache_bounds_redirection_and_rate_limits(monkeypatch):
    count=[];monkeypatch.setattr(sp,'_last',{});monkeypatch.setattr(sp,'_cooldown',{})
    def handler(request):count.append(request);return httpx.Response(200,json={'results':[FIXTURE['openalex']]})
    monkeypatch.setattr(sp,'HTTP_TRANSPORT',httpx.MockTransport(handler))
    budget=sp.RequestBudget();provider=sp.OpenAlex()
    first=provider.search('cache-'+uid(),budget);query=count[0].url.params['search']
    again=provider.search(query,budget)
    assert len(count)==1 and budget.cache_hits==1 and first[0].retrieved_at==again[0].retrieved_at
    monkeypatch.setattr(sp,'HTTP_TRANSPORT',httpx.MockTransport(lambda request:httpx.Response(200,json=FIXTURE['openalex'])))
    with pytest.raises(sp.ScholarlyError,match='did not match'):provider.resolve('openalex','W9999999999999999',sp.RequestBudget())
    monkeypatch.setattr(sp,'HTTP_TRANSPORT',httpx.MockTransport(lambda request:httpx.Response(302,headers={'location':'http://127.0.0.1/secrets'})))
    with pytest.raises(sp.ScholarlyError,match='redirect'):sp.OpenAlex().search(uid(),sp.RequestBudget())
    monkeypatch.setattr(sp,'HTTP_TRANSPORT',httpx.MockTransport(lambda request:httpx.Response(429,headers={'retry-after':'60'})))
    with pytest.raises(sp.ScholarlyError,match='429'):sp.OpenAlex().search(uid(),sp.RequestBudget())
    with pytest.raises(sp.ScholarlyError,match='cooling'):sp.OpenAlex().search(uid(),sp.RequestBudget())
    with pytest.raises(sp.ScholarlyError):sp.RequestBudget(maximum=0).consume()


def test_ground_review_accept_reject_stale_and_shared_graph(setup):
    pid,base,h=project();r=search(base,h)
    assert r['status']=='completed',r.get('error')
    assert len(get(base+'/objects'))==1  # No silent scientific mutation.
    candidates=get(base+'/literature/sources?run_id='+r['id']);assert len(candidates)==1
    p=get(base+'/research-runs/'+r['id']+'/proposals')[0]
    assert p['payload']['literature']['classification']=='qualifies'
    path=base+'/research-runs/'+r['id']+'/proposals/'+p['id']+'/accept'
    accepted=post(path);assert post(path)['result_ids']==accepted['result_ids']
    loaded=get(base);assert any(o['id']==accepted['result_ids']['paper_object_id'] for o in loaded['objects'])
    assert any(p['objectId']==accepted['result_ids']['paper_object_id'] for p in loaded['placements'])
    edge=next(e for e in get(base+'/relationships') if e['id']==accepted['result_ids']['relationship_id'])
    assert edge['relationship_type']=='related_to' and edge['details']['literature_classification']=='qualifies'
    assert get(base+'/runs')==[] and get(base+'/evidence')==[]
    assert get(base+'/objects/'+accepted['result_ids']['object_id'])['metadata']['source_type']=='literature'
    assert get(base+'/objects/'+accepted['result_ids']['object_id']+'/revisions')
    assert any(e['event_type']=='literature_interpretation_accepted' for e in get(base+'/events'))
    again=search(base,h,action='challenge');p2=get(base+'/research-runs/'+again['id']+'/proposals')[0]
    assert any(q['strategy']=='alternative' for q in again['output']['queries'])
    assert 'No genuine contradiction' in again['output']['disagreements'][0]
    post(base+'/research-runs/'+again['id']+'/proposals/'+p2['id']+'/reject',{'rationale':'Insufficient evidence for my claim.'})
    assert get(base+'/research-runs/'+again['id']+'/proposals')[0]['status']=='rejected'
    newer=search(base,h);p3=get(base+'/research-runs/'+newer['id']+'/proposals')[0]
    client.patch('/v1/'+base+'/objects/'+h['id'],json={'body':'A changed hypothesis.'})
    assert client.post('/v1/'+base+'/intelligence/proposals/'+p3['id']+'/accept',json={}).status_code==409


def test_model_outage_keeps_verified_sources_and_metadata_only_useful(setup,monkeypatch):
    _,base,h=project()
    class Unavailable:
        def generate_structured_response(self,request):raise ProviderError('model_unavailable','Configured model overloaded.')
    monkeypatch.setattr(lit,'route',lambda *a:('Google Gemini','unavailable',Unavailable()))
    result=search(base,h);assert result['status']=='failed' and 'overloaded' in result['error']
    source=get(base+'/literature/sources?run_id='+result['id'])[0]
    assert source['identifiers']['doi'] and source['abstract']
    assert len(get(base+'/objects'))==1
    post(base+'/literature/sources/'+source['source_id']+'/save')
    metadata=search(base,h,use_model=False);assert metadata['status']=='completed' and metadata['output']['analyzed_papers']==0


def test_invalid_doi_cross_project_and_source_injection_do_not_create_records(setup):
    _,base,h=project()
    before=len(get(base+'/objects'))
    assert client.post('/v1/'+base+'/literature/resolve',json={'identifier':'http://localhost/admin'}).status_code==422
    assert client.post('/v1/'+base+'/literature/resolve',json={'identifier':'10.9999/nonexistent-vectorheart-test'}).status_code==404
    assert len(get(base+'/objects'))==before
    r=search(base,h);sid=get(base+'/literature/sources?run_id='+r['id'])[0]['source_id']
    _,other,_=project();assert client.get('/v1/'+other+'/literature/sources/'+sid).status_code==404
    assert client.post('/v1/'+other+'/literature/runs',json={'object_ids':[h['id']],'idempotency_key':uid()}).status_code==404
    source=get(base+'/literature/sources/'+sid)
    assert source['bibliographic_status']=='provider_verified'
    assert all('UNTRUSTED' in request.system for request in setup.calls)


def test_unsupported_findings_and_fabricated_numerical_claims_are_withheld(setup):
    _,base,h=project();r=search(base,h);source=get(base+'/literature/sources?run_id='+r['id'])[0]
    with Session() as s:
        run=s.get(stage3.ResearchRun,r['id']);model=LiteratureAnalysis.model_validate({'summary':'','findings':[{'snapshot_id':source['snapshot_id'],'target_object_id':h['id'],'classification':'supports','claim':'Myopia fell by 99999 percent.','rationale':'Not legitimate.','passage':source['abstract'][:80],'limitations':[],'method_notes':[],'missing_information':[]}],'disagreements':[],'limitations':[]})
        with pytest.raises(ValueError,match='numerical'):lit.validate_finding(s,run.project_id,run,model.findings[0],{source['snapshot_id']})
        model.findings[0].snapshot_id='invented'
        with pytest.raises(ValueError,match='not retrieved'):lit.validate_finding(s,run.project_id,run,model.findings[0],{source['snapshot_id']})


def test_accelerate_uses_actual_literature_and_preserves_canonical_citations(setup):
    _,base,h=project();litrun=search(base,h)
    p=get(base+'/research-runs/'+litrun['id']+'/proposals')[0];post(base+'/intelligence/proposals/'+p['id']+'/accept')
    run=post(base+'/research-runs',{'kind':'accelerate','objective':'Find a useful literature-informed boundary condition.','idempotency_key':uid()})
    result=get(base+'/research-runs/'+run['id']);assert result['status']=='completed',result.get('error')
    proposal=get(base+'/research-runs/'+run['id']+'/proposals')[0]
    assert proposal['payload']['literature_source_ids']
    accepted=post(base+'/intelligence/proposals/'+proposal['id']+'/accept')
    obj=get(base+'/objects/'+accepted['result_ids']['object_id'])
    assert obj['metadata']['model_provenance']['literature_references'][0]['snapshot_id']
    assert accepted['result_ids']['source_object_ids']


def test_bounded_agent_selects_real_tool_path_and_reasons_over_returned_records(setup):
    _,base,h=project()
    r=post(base+'/research-runs',{'kind':'investigate','objective':'Use literature to choose a scientifically useful next hypothesis.','max_steps':3,'idempotency_key':uid()})
    done=get(base+'/research-runs/'+r['id']);assert done['status']=='completed',done.get('error')
    assert done['steps_used']==2 and done['tool_executions']==1
    step=next(s for s in done['steps'] if s['kind']=='literature_tool')
    assert step['input']['tool_request']['tool']=='literature.search'
    assert step['result']['sources'][0]['identifiers']['doi']=='10.1371/journal.pone.0181772'
    assert setup.calls[-1].context['literature'][0]['abstract']
    assert get(base+'/runs')==[] and get(base+'/evidence')==[]
    assert len(get(base+'/objects'))==1
    assert get(base+'/research-runs/'+r['id']+'/proposals')[0]['payload']['literature_source_ids']
    post(base+'/research-runs/'+r['id']+'/resume');assert get(base+'/research-runs/'+r['id'])['tool_executions']==1


def test_exact_source_reference_roles_are_normalized_without_inventing_citations(setup):
    pid,base,h=project();r=search(base,h);source=get(base+'/literature/sources?run_id='+r['id'])[0]
    context={'objects':[{'id':h['id']}],'literature':[source]}
    p=scientific_proposal(source['source_id'])
    response=ResearchIntelligenceResponse(answer='Based on supplied sources.',uncertainties=[],context_references=[h['id'],source['source_id'],source['snapshot_id']],proposals=[p],limitations=[])
    normalized=lit.normalize_research_citations(response,context)
    assert normalized.context_references==[h['id']]
    assert normalized.literature_references==[source['source_id']]
    assert normalized.proposals[0].referenced_object_ids==[]
    assert normalized.proposals[0].literature_source_ids==[source['source_id']]
    assert normalized.proposals[0].content==response.proposals[0].content
    with Session() as s:
        intelligence.validated_proposal(s,pid,normalized.proposals[0],context)
        invalid=normalized.proposals[0].model_copy(update={'literature_source_ids':['invented-source']})
        with pytest.raises(ValueError,match='not supplied'):intelligence.validated_proposal(s,pid,invalid,context)


def test_all_tool_returned_sources_are_in_the_explicit_citation_allowlist(setup,monkeypatch):
    from app.stage3_models import ResearchStep
    pid,base,h=project();monkeypatch.setattr(stage3,'schedule',lambda *a:None)
    r=post(base+'/research-runs',{'kind':'investigate','objective':'Inspect all actual returned source records.','idempotency_key':uid()})
    with stage3.kernel().transaction() as s:
        run=s.get(stage3.ResearchRun,r['id']);returned=[]
        for i,reference in enumerate(FIXTURE['openalex']['referenced_works'][:8]):
            # Synthetic metadata for an explicit allowlist test; no live verification claim.
            paper=sp.normalize_openalex(FIXTURE['openalex']).model_copy(update={'identifiers':{'openalex':reference.rsplit('/',1)[-1]},'title':f'Allowlist fixture {i}'})
            snapshot=lit.store_hit(s,pid,run.id,paper,'fixture','agent_selected',i)
            returned.append(lit.source_view(s,snapshot))
        st=stage3.step(s,run,'literature_tool',{'tool_request':{'tool':'literature.search'}});st.status='completed';st.result={'sources':returned}
        conv=intelligence.ResearchConversation(project_id=pid);s.add(conv);s.flush()
        context,_=stage3.investigation_context(s,pid,run,conv.id)
        assert {v['source_id'] for v in returned}.issubset({v['source_id'] for v in context['literature']})
        assert all('abstract' not in v for v in context['investigation_trace'][0]['result']['sources'])


def test_metadata_only_support_and_fabricated_citation_links_are_rejected(setup):
    _,base,h=project();r=search(base,h)
    with Session() as s:
        run=s.get(stage3.ResearchRun,r['id']);source=get(base+'/literature/sources?run_id='+r['id'])[0]
        snap=s.get(SourceSnapshot,source['snapshot_id'])
        bad=LiteratureAnalysis.model_validate({'summary':'','findings':[{'snapshot_id':snap.id,'target_object_id':h['id'],'classification':'cites','claim':'This source cites the hypothesis.','rationale':'Unsupported bibliographic reference.','passage':snap.record['title'],'limitations':[],'method_notes':[],'missing_information':[]}],'disagreements':[],'limitations':[]}).findings[0]
        with pytest.raises(ValueError,match='paper target|paper object'):lit.validate_finding(s,run.project_id,run,bad,{snap.id})
    with stage3.kernel().transaction() as s:
        run=s.get(stage3.ResearchRun,r['id'])
        metadata=sp.normalize_openalex(FIXTURE['openalex']).model_copy(update={'abstract':'','access_level':'metadata'})
        _,snapshot=lit.persist_paper(s,metadata)
        bad.snapshot_id=snapshot.id;bad.classification='supports';bad.passage=metadata.title
        with pytest.raises(ValueError,match='Metadata/title'):lit.validate_finding(s,run.project_id,run,bad,{snapshot.id})
        bad.classification='background'
        assert lit.validate_finding(s,run.project_id,run,bad,{snapshot.id}).access_level=='metadata'


def test_accepted_literature_claim_can_motivate_kernel_revision_without_fake_run(setup):
    _,base,h=project();r=search(base,h);p=get(base+'/research-runs/'+r['id']+'/proposals')[0]
    accepted=post(base+'/intelligence/proposals/'+p['id']+'/accept');claim=accepted['result_ids']['object_id']
    operation=post(base+'/operations',{'action_type':'modify.propose_hypothesis_revision','target_object_ids':[h['id']],'proposal_payload':{'original_statement':h['body'],'proposed_statement':'Exposure feasibility should be distinguished from clinical myopia-prevention efficacy.','evidence_ids':[claim],'assumptions_changed':[],'scope':'Only the reported feasibility study.','remaining_uncertainties':['Clinical efficacy remains unresolved.'],'rationale':'Accepted abstract-grounded interpretation motivates a narrower claim.'}})
    post(base+'/operations/'+operation['id']+'/approve');post(base+'/operations/'+operation['id']+'/execute')
    assert len(get(base+'/objects/'+h['id']+'/revisions'))==2
    assert get(base+'/runs')==[] and get(base+'/evidence')==[]


def test_invalid_tool_names_and_foreign_sources_cannot_bypass_readonly_registry(setup):
    pid,base,h=project()
    with Session() as s:
        with pytest.raises(ValueError):lit.validate_tool(s,pid,{'tool':'shell.exec','query':'anything','identifier':None,'source_id':None,'rationale':'Malicious source instruction.'})
        with pytest.raises(ValueError):lit.validate_tool(s,pid,{'tool':'literature.resolve_identifier','query':None,'identifier':'http://169.254.169.254/latest/meta-data','source_id':None,'rationale':'Malicious external URL.'})
    _,other,other_h=project();r=search(other,other_h);sid=get(other+'/literature/sources?run_id='+r['id'])[0]['source_id']
    with Session() as s:
        with pytest.raises(stage3.kernel().Problem):lit.validate_tool(s,pid,{'tool':'literature.inspect_source','query':None,'identifier':None,'source_id':sid,'rationale':'Not retrieved in this project.'})


def test_analysis_recovery_reuses_snapshots_and_partial_invalid_findings_preserve_valid(setup,monkeypatch):
    _,base,h=project();metadata=search(base,h,use_model=False)
    class Partial(FixtureModel):
        def generate_structured_response(self,request):
            result=super().generate_structured_response(request)
            if request.schema is LiteratureAnalysis:
                valid=result.output.findings[0]
                result.output.findings.append(valid.model_copy(update={'snapshot_id':'not-retrieved'}))
            return result
    monkeypatch.setattr(lit,'route',lambda *a:('Google Gemini','fixture',Partial()))
    again=post(base+'/literature/runs/'+metadata['id']+'/analyze');result=get(base+'/research-runs/'+again['id'])
    assert result['status']=='completed' and result['output']['withheld']
    assert len(get(base+'/research-runs/'+again['id']+'/proposals'))==1
    assert result['output']['retrieval']['network_requests']==0
    assert result['output']['retrieval']['source_run_id']==metadata['id']
    assert len(get(base+'/objects'))==1


def test_repeated_search_acceptance_reuses_paper_and_identical_claim_without_graph_flood(setup):
    _,base,h=project();first=search(base,h);p=get(base+'/research-runs/'+first['id']+'/proposals')[0]
    a=post(base+'/intelligence/proposals/'+p['id']+'/accept');count=len(get(base+'/objects'))
    second=search(base,h);p2=get(base+'/research-runs/'+second['id']+'/proposals')[0]
    b=post(base+'/intelligence/proposals/'+p2['id']+'/accept')
    assert a['result_ids']==b['result_ids'] and len(get(base+'/objects'))==count


def test_bibliographic_citation_requires_a_real_returned_reference_without_implying_agreement(setup):
    pid,base,h=project();r=search(base,h)
    with stage3.kernel().transaction() as s:
        run=s.get(stage3.ResearchRun,r['id'])
        target_snapshot=lit.store_hit(s,pid,run.id,sp.normalize_openalex(FIXTURE['reference']),'verified reference','bibliographic_reference',0)
        paper=lit.make_paper_object(s,pid,target_snapshot)
        source=next(snap for snap in s.scalars(select(SourceSnapshot).where(SourceSnapshot.provider=='OpenAlex')) if snap.record['identifiers'].get('doi')=='10.1371/journal.pone.0181772')
        run.snapshot={**run.snapshot,'targets':lit.target_context(s,pid,[paper.id])}
        finding=LiteratureAnalysis.model_validate({'summary':'Bibliographic reference only.','findings':[{'snapshot_id':source.id,'target_object_id':paper.id,'classification':'cites','claim':'The publication lists this work in its references.','rationale':'A bibliographic citation is not scientific agreement.','passage':source.record['title'],'limitations':['No support/challenge inferred.'],'method_notes':[],'missing_information':[]}],'disagreements':[],'limitations':[]}).findings[0]
        validated=lit.validate_finding(s,pid,run,finding,{source.id})
        assert validated.classification=='cites' and validated.access_level=='metadata'
        assert lit.RELATION_TYPES[validated.classification]=='related_to'
