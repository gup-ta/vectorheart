"""Explicit test-only service entry point. Never imported by the production app."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.intelligence_schemas import ResearchIntelligenceResponse
from app.model_providers import ModelResponse
from app.stage3_schemas import GraphExtraction
import app.stage3 as stage3
import app.literature as literature
from app.literature_schemas import SearchPlan,LiteratureAnalysis
from app.scholarly_providers import normalize_openalex,normalize_pmc,normalize_crossref,ScholarlyError
import json
import app.intelligence as intelligence

class UITestProvider:
    def generate_structured_response(self,request):
        # Only deterministic fixtures used by frontend tests; never a production fallback.
        if request.schema is SearchPlan:
            return ModelResponse(SearchPlan(queries=[{'strategy':'methodological','query':'myopia bright classroom','rationale':'Test-only search plan.'}],limitations=['Fixture inference.']))
        if request.schema is LiteratureAnalysis:
            source=request.context['sources'][0];target=request.context['research_objects'][0]['id']
            return ModelResponse(LiteratureAnalysis(summary='The source reports feasibility, not clinical efficacy.',findings=[{'snapshot_id':source['snapshot_id'],'target_object_id':target,'classification':'qualifies','claim':'The study assessed light characteristics and user acceptability.','rationale':'Feasibility does not establish a clinical myopia effect.','passage':source['abstract'][:80],'limitations':['Abstract only.'],'method_notes':['Questionnaires and light measurements.'],'missing_information':['Clinical causal efficacy not established.']}],disagreements=[],limitations=['Fixture inference; real recorded CC-BY metadata.']))
        if request.schema is GraphExtraction:
            source=request.context['passages'][0]
            passage={'object_id':source['id'],'revision':source['revision'],'excerpt':source['body'][:80]}
            return ModelResponse(GraphExtraction(summary='Test-only source reconstruction.',nodes=[{'key':'claim','existing_object_id':None,'object_type':'hypothesis','title':'A journal-grounded hypothesis','body':'An interpretation of the original record.','rationale':'The journal supplied the source passage.','uncertainty':'inferred','sources':[passage]}],edges=[],limitations=['Test fixture, not live inference.']))
        source=request.context['objects'][0]['id'] if request.context['objects'] else None
        proposal={'action_type':'create_question','title':'An accepted intelligence question','content':'Which assumptions need independent measurements?','rationale':'Fixture for proposal review integration.','assumptions':[],'predictions':[],'limitations':['Test fixture response'],'referenced_object_ids':[source] if source else [],'target_object_id':None,'adapter_id':None,'adapter_parameters':None,'evidence_ids':[]}
        if 'AI Accelerate:' in request.system:
            proposal={**proposal,'action_type':'create_hypothesis','title':'A novel Accelerate hypothesis','content':'The interaction of outdoor light and near-work changes the reported association.'}
        return ModelResponse(ResearchIntelligenceResponse(answer='Deterministic test provider response grounded in supplied object IDs.',uncertainties=['Test-only response'],context_references=[source] if source else [],proposals=[proposal],limitations=['No paid model call in this test.']))
if __name__=='__main__':
    import uvicorn
    class UIArchive:
        def __init__(self,name):self.name=name
        def paper(self):
            records=json.loads((Path(__file__).parent/'fixtures/literature.json').read_text(encoding='utf-8'))
            return {'OpenAlex':normalize_openalex,'Europe PMC':normalize_pmc,'Crossref':normalize_crossref}[self.name](records[{'OpenAlex':'openalex','Europe PMC':'pmc','Crossref':'crossref'}[self.name]])
        def search(self,query,budget):return [self.paper()]
        def resolve(self,kind,value,budget):
            p=self.paper()
            if p.identifiers.get(kind)!=value:raise ScholarlyError(self.name,'not_found','Fixture identifier was not found.')
            return p
    literature.PROVIDERS={name:UIArchive(name) for name in ['OpenAlex','Europe PMC','Crossref']}
    literature.route=lambda *args:('Test provider','test-only-model',UITestProvider())
    intelligence.route=lambda *args:('Test provider','test-only-model',UITestProvider())
    stage3.route=lambda *args:('Test provider','test-only-model',UITestProvider())
    uvicorn.run(app,host='127.0.0.1',port=8002,log_level='warning')
