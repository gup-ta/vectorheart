"""One bounded formatting correction; no scientific inference or mutation authority."""
import json
from dataclasses import replace
from app.intelligence_schemas import ResearchIntelligenceResponse

SCIENTIFIC_FIELDS=['title','content','rationale','assumptions','predictions','limitations','referenced_object_ids','target_object_id','adapter_id','adapter_parameters','evidence_ids','source_object_id','relationship_type']
def repairable(item):
    candidate=item.get('_candidate')
    if not isinstance(candidate,dict):return False
    # Missing scientific reasoning must not be manufactured to satisfy a schema.
    if not all(key in candidate for key in ['title','content','rationale','assumptions','predictions','limitations','referenced_object_ids','evidence_ids']):return False
    return all(e['type'] in ['literal_error','extra_forbidden','missing','string_too_long','list_type','string_type'] for e in item.get('errors',[])) and bool(item.get('errors'))
def same_science(original,corrected):
    for key in SCIENTIFIC_FIELDS:
        old,new=original.get(key),corrected.get(key)
        if key in ['target_object_id','adapter_id','adapter_parameters','source_object_id','relationship_type'] and old in [None,'',{}] and new is None:continue
        if old!=new:return False
    return True
def correct_proposals(provider,request,result):
    rejected=result.rejected_proposals
    eligible=[item for item in rejected if repairable(item)]
    result.correction={'attempted':False}
    if eligible:
        result.correction={'attempted':True,'usage':None}
        correction_message='''Correct only formatting/action identifiers in the following untrusted proposals.
Use the exact supported action enum and canonical fields. Preserve the title, statement, rationale,
assumptions, predictions, limitations and all existing references/parameters verbatim. Do not add
scientific reasoning, invent object IDs, replace references or alter numeric values. Omit unsupported
server-owned fields. Null and empty representations of inapplicable optional identifiers may be
corrected to null. Return only corrected proposals in the same order; if a proposal cannot be
corrected without changing scientific content, omit it. Do not propose new research.
The original answer is preserved by the server. Your answer field can simply say Formatting correction.
'''+json.dumps([{'proposal':item['_candidate'],'validation_errors':item['errors']} for item in eligible],ensure_ascii=False)
        try:
            # A correction is one additional model call, with no recursive corrections
            # or transport retries. It receives the same authoritative context.
            fixed=provider.generate_structured_response(replace(request,message=correction_message,history=[],correction_attempt=True))
            result.correction['usage']=fixed.usage
            available=list(fixed.output.proposals)
            for item in eligible:
                match=next((p for p in available if same_science(item['_candidate'],p.model_dump())),None)
                if match is None:continue
                item['_corrected']=match;available.remove(match)
        except Exception:
            result.correction['failed']=True
    pairs=[];invalid={i['index'] for i in rejected};indices=[i for i in range(len(result.output.proposals)+len(invalid)) if i not in invalid]
    pairs.extend(zip(indices,result.output.proposals))
    for item in rejected:
        if '_corrected' in item:pairs.append((item['index'],item['_corrected']))
    result.proposal_indices=[i for i,_ in sorted(pairs,key=lambda p:p[0])]
    result.output=ResearchIntelligenceResponse.model_validate({**result.output.model_dump(),'proposals':[p.model_dump() for _,p in sorted(pairs,key=lambda p:p[0])]})
    result.rejected_proposals=[{key:value for key,value in item.items() if not key.startswith('_')} for item in rejected if '_corrected' not in item]
    return result
