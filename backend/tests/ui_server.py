"""Explicit test-only service entry point. Never imported by the production app."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.intelligence_schemas import ResearchIntelligenceResponse
from app.model_providers import ModelResponse
from app.stage3_schemas import GraphExtraction
import app.stage3 as stage3
import app.intelligence as intelligence

class UITestProvider:
    def generate_structured_response(self,request):
        # Only deterministic fixtures used by frontend tests; never a production fallback.
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
    intelligence.route=lambda *args:('Test provider','test-only-model',UITestProvider())
    stage3.route=lambda *args:('Test provider','test-only-model',UITestProvider())
    uvicorn.run(app,host='127.0.0.1',port=8002,log_level='warning')
