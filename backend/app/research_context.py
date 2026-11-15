import json
import os
from sqlalchemy import select
from app.db import Project,Object,Relationship,Revision,Event,Evidence,Run
from app.intelligence_models import ResearchMessage
from app.science import ADAPTER,Parameters,LIMITATIONS

def context_limit():return max(4000,min(48000,int(os.getenv('VECTORHEART_CONTEXT_CHARS','24000'))))
class ResearchContextBuilder:
    def build(self,s,pid,selected_id,conversation_id,question):
        from app.main import get,Problem
        project=get(s,Project,pid)
        selected=get(s,Object,selected_id,pid) if selected_id else None
        objects=s.scalars(select(Object).where(Object.project_id==pid,Object.deleted==False).order_by(Object.updated_at.desc(),Object.id)).all()
        relationships=s.scalars(select(Relationship).where(Relationship.project_id==pid)).all()
        neighbors={r.target_object_id if r.source_object_id==selected_id else r.source_object_id for r in relationships if selected_id in [r.source_object_id,r.target_object_id]}
        words=set(question.lower().split())
        ordered=sorted(objects,key=lambda o:(0 if o.id==selected_id else 1 if o.id in neighbors else 2 if o.object_type in ['evidence','experiment','hypothesis','question','observation'] else 3,-sum(w in (o.title+' '+o.body).lower() for w in words if len(w)>3)))
        context={'project':{'id':pid,'title':project.title[:120],'description':project.description[:1500],'question':project.question[:1500],'research_field':str(project.settings.get('researchField',''))[:200]},'selected_object_id':selected_id,'objects':[],'relationships':[],'evidence':[],'literature':[],'events':[],'adapters':[{'id':ADAPTER,'parameter_schema':Parameters.model_json_schema(),'scope':'Only the registered synthetic A/B models; target must have causal_demo metadata. Unknown adapters are conceptual, not executable.','limitations':LIMITATIONS}],'omitted_objects':0,'truncated':False}
        limit=context_limit()
        def size():return len(json.dumps(context,ensure_ascii=False))
        if size()>limit-1800:
            context['project']['description']=project.description[:256];context['project']['question']=project.question[:256];context['truncated']=True
        def append(key,value):
            context[key].append(value)
            if size()>limit-150:context[key].pop();context['truncated']=True;return False
            return True
        for o in ordered:
            rev=s.scalar(select(Revision).where(Revision.object_id==o.id,Revision.revision_number==o.current_revision))
            metadata={k:v for k,v in o.scientific_metadata.items() if k in ['statement','assumptions','predicted_outcomes','limitations','epistemic_status','source_type','verification_status','run_id','candidate_world','causal_demo','revision_scope','remaining_uncertainties']}
            # Bound individual fields; keep complete objects/JSON with explicit excerpt markers.
            row={'id':o.id,'revision_number':o.current_revision,'revision_id':rev.revision_id if rev else None,'object_type':o.object_type,'title':o.title[:200],'body':o.body[:3000],'metadata':metadata,'provenance_type':o.provenance_type,'verification_status':metadata.get('verification_status','unverified'),'content_excerpted':len(o.body)>3000}
            if len(json.dumps(metadata))>4000:row['metadata']={'omitted_oversized_metadata':True};row['content_excerpted']=True
            if not append('objects',row):context['omitted_objects']+=1
            elif row['content_excerpted']:context['truncated']=True
        included={o['id'] for o in context['objects']}
        if selected and selected.id not in included:raise Problem('Selected object exceeds context budget; shorten it or increase the server context limit',422)
        for r in relationships:
            if r.source_object_id in included and r.target_object_id in included:append('relationships',{'id':r.id,'source_id':r.source_object_id,'target_id':r.target_object_id,'type':r.relationship_type})
        for e in s.scalars(select(Evidence).where(Evidence.project_id==pid).order_by(Evidence.created_at.desc()).limit(6)):
            if e.id not in included:continue
            run=s.get(Run,e.source_run_id)
            append('evidence',{'object_id':e.id,'source_type':e.source_type,'verification_status':e.verification_status,'target_hypothesis_ids':[i for i in e.target_hypothesis_ids if i in included],'measured_results':{k:v for k,v in e.measured_results.items() if k in ['mean','std','se','confidence_interval','predictions','compatible']},'actual_parameters':run.actual_parameters,'validation_results':run.validation_results,'limitations':e.limitations})
        for e in s.scalars(select(Event).where(Event.project_id==pid).order_by(Event.project_sequence_number.desc()).limit(8)):
            append('events',{'sequence':e.project_sequence_number,'event_type':e.event_type,'object_ids':[i for i in e.affected_object_ids if i in included]})
        from app.stage3 import corrections
        decisions=corrections(s,pid)
        if decisions:append('events',{'researcher_corrections':decisions,'instruction':'These are durable human interpretation constraints, not verified evidence.'})
        from app.literature import project_literature_context
        for source in project_literature_context(s,pid,selected_ids=([selected_id] if selected_id else [])+list(neighbors)):append('literature',source)
        messages=s.scalars(select(ResearchMessage).where(ResearchMessage.conversation_id==conversation_id,ResearchMessage.status=='completed').order_by(ResearchMessage.created_at.desc(),ResearchMessage.id).limit(8)).all()
        history=[{'role':m.role,'content':m.content[:1500]} for m in reversed(messages)]
        # Credentials are never configuration context. Redact known keys if pasted into source text.
        def scrub(value):
            raw=json.dumps(value,ensure_ascii=False)
            for key in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','OPENALEX_API_KEY']:
                secret=os.getenv(key)
                if secret:raw=raw.replace(json.dumps(secret)[1:-1],'[credential redacted]')
            return json.loads(raw)
        return scrub(context),scrub(history)
