"""Explicit test-only service entry point. Never imported by the production app."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.intelligence_schemas import ResearchIntelligenceResponse
from app.model_providers import ModelResponse
import app.intelligence as intelligence

class UITestProvider:
    def generate_structured_response(self,request):
        # Only deterministic fixtures used by frontend tests; never a production fallback.
        source=request.context['objects'][0]['id'] if request.context['objects'] else None
        proposal={'action_type':'create_question','title':'An accepted intelligence question','content':'Which assumptions need independent measurements?','rationale':'Fixture for proposal review integration.','assumptions':[],'predictions':[],'limitations':['Test fixture response'],'referenced_object_ids':[source] if source else [],'target_object_id':None,'adapter_id':None,'adapter_parameters':None,'evidence_ids':[]}
        return ModelResponse(ResearchIntelligenceResponse(answer='Deterministic test provider response grounded in supplied object IDs.',uncertainties=['Test-only response'],context_references=[source] if source else [],proposals=[proposal],limitations=['No paid model call in this test.']))
if __name__=='__main__':
    import uvicorn
    intelligence.route=lambda *args:('Test provider','test-only-model',UITestProvider())
    uvicorn.run(app,host='127.0.0.1',port=8002,log_level='warning')
