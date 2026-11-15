import assert from 'node:assert/strict';
import { test } from 'node:test';
import { overlayFor } from '../src/components/graph-intelligence.tsx';
import { newProject, newObject } from '../src/lib/projects.ts';

test('Accelerate proposals are spatial provisional nodes and links, never accepted objects',()=>{
  const project=newProject('Research','');const h=newObject(project.id,'Hypothesis'),q=newObject(project.id,'Question');
  project.objects=[h,q];
  const run={kind:'accelerate',status:'completed',steps:[],output:{}};
  const base={status:'pending',result_ids:{},payload:{title:'New hypothesis',content:'A possible mechanism',rationale:'Testable alternative',referenced_object_ids:[h.id],target_object_id:null}};
  const proposals=[{...base,id:'one',action_type:'create_hypothesis'},{...base,id:'two',action_type:'propose_relationship',payload:{...base.payload,source_object_id:h.id,target_object_id:q.id,relationship_type:'challenges'}}];
  const overlay=overlayFor(run,proposals,project);
  const novel=overlay.nodes.find(n=>n.id==='proposal-one');
  assert.equal(novel.metadata.origin,'ai_accelerate');assert.equal(novel.metadata.provisional,true);
  assert.ok(overlay.edges.some(e=>e.id==='proposal-two'&&e.sourceId===h.id&&e.targetId===q.id&&e.novel));
  assert.equal(project.objects.length,2);
  proposals[0].status='accepted';assert.ok(!overlayFor(run,proposals,project).nodes.some(n=>n.id==='proposal-one'));
});

test('graph reconstruction remains visually distinct from novel discovery and preserves source IDs',()=>{
  const project=newProject('Research','');
  const run={kind:'graph',status:'review',steps:[],output:{nodes:[{id:'stable-id',object_type:'question',title:'Uncertainty',body:'What remains unknown?',rationale:'From source',uncertainty:'inferred'}],edges:[]}};
  const overlay=overlayFor(run,[],project);
  assert.equal(overlay.nodes[0].id,'stable-id');assert.equal(overlay.nodes[0].metadata.origin,'model_interpretation');
  run.status='accepted';assert.equal(overlayFor(run,[],project).nodes.length,0);
});
