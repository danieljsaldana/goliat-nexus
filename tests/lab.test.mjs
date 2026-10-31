import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createStory,advanceStory,recoverStory,duplicateStory,storyData,requestSteps} from '../site/lab.js';
test('the normal example persists a request before queue delivery and records one activity',()=>{
 let state=createStory('access');
 for(const step of requestSteps){state=advanceStory(state);if(step==='cosmos'){assert.equal(state.saved,true);assert.equal(state.outboxPending,true);assert.equal(state.deliveries,0);}}
 assert.equal(state.activities,1);assert.equal(state.deliveries,1);assert.equal(state.outboxPending,false);
 const data=storyData(state);assert.equal(data.request.id,data.activity.request_id);assert.equal(data.event.id,data.activity.id);
});
test('failed publishing retains the request; the recovery timer resumes the same event',()=>{
 let state=createStory('support');for(let i=0;i<4;i++)state=advanceStory(state,{failQueue:true});
 assert.equal(state.paused,true);assert.equal(state.saved,true);assert.equal(state.outboxPending,true);assert.equal(state.activities,0);
 assert.deepEqual(advanceStory(state),state);
 state=recoverStory(state);state=advanceStory(advanceStory(state));
 assert.equal(state.activities,1);assert.equal(state.recovered,true);assert.equal(state.outboxPending,false);
});
test('replaying delivery never invents another business activity',()=>{
 let state=createStory('maintenance');for(const step of requestSteps)state=advanceStory(state);
 state=duplicateStory(duplicateStory(state));assert.equal(state.deliveries,3);assert.equal(state.activities,1);
 assert.throws(()=>recoverStory(state));assert.throws(()=>duplicateStory(createStory()));assert.throws(()=>createStory('unknown'));
});
