import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createApi} from '../apps/api/server.mjs';
import {MemoryRepository,eventFor,requestData,validateUri,TENANT} from '../apps/api/domain.mjs';
import {processEvent,recoverOutbox} from '../apps/functions/handlers.mjs';
const actor={tenantId:TENANT,objectId:'44444444-4444-4444-8444-444444444444',roles:['Requester']};
const payload={id:'11111111-1111-4111-8111-111111111111',title:'Acceso a documentación',category:'access'};
async function runApi(t,options){const api=createApi({authenticate:async()=>actor,...options});await new Promise(resolve=>api.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>api.close(resolve)));return `http://127.0.0.1:${api.address().port}`;}
test('frontend request → Node API → pending outbox → Function activity; duplicate deliveries are safe',async t=>{
 const repo=new MemoryRepository(),queue=[];
 const base=await runApi(t,{getRepository:async()=>repo,publish:async()=>{throw new Error('queue unavailable');}});
 const submit=()=>fetch(base+'/api/tenant/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 assert.equal((await submit()).status,202);assert.equal((await submit()).status,200);assert.equal((await repo.pending()).length,1);
 await recoverOutbox(repo,async(r,document)=>{queue.push(eventFor(document));await r.sent(document.id);});
 assert.equal(queue.length,1);assert.equal((await repo.pending()).length,0);
 await processEvent(JSON.stringify(queue[0]),repo);await processEvent(queue[0],repo);
 const requests=await(await fetch(base+'/api/tenant/requests')).json();const activities=await(await fetch(base+'/api/activities/events')).json();
 assert.equal(requests.items.length,1);assert.equal(requests.items[0].status,'processed');assert.equal(activities.items.length,1);assert.equal(activities.items[0].request_id,payload.id);
});
test('invalid JSON and Mongo operator-shaped input never reach storage',async t=>{
 let reached=false;const base=await runApi(t,{getRepository:async()=>{reached=true;throw new Error();}});
 for(const body of ['{',JSON.stringify({...payload,title:{$ne:null}})]){
  const result=await fetch(base+'/api/tenant/requests',{method:'POST',headers:{'Content-Type':'application/json'},body});assert.equal(result.status,400);
 }
 assert.equal(reached,false);
});
test('data failure returns 503 without SDK details; API role is enforced',async t=>{
 const base=await runApi(t,{role:'activities',getRepository:async()=>{throw new Error('secret-value');}});
 const result=await fetch(base+'/readyz');assert.equal(result.status,503);assert.doesNotMatch(await result.text(),/secret-value/);
 assert.equal((await fetch(base+'/api/tenant/requests')).status,404);
});
test('duplicate UUID with other content and malformed events are rejected',async()=>{
 const repo=new MemoryRepository();await repo.create(payload,actor);
 await assert.rejects(repo.create({...payload,title:'Different request'},actor));
 await assert.rejects(processEvent({id:'invalid'},repo));
 assert.throws(()=>requestData({...payload,title:{$ne:null}}));
});
test('Cosmos connection must use the configured Mongo host and TLS',()=>{
 const host='cosmos-test.mongo.cosmos.azure.com';
 const valid=`mongodb://user:encodedpassword@${host}:10255/?ssl=true&retrywrites=false`;
 assert.equal(validateUri(valid,host),valid);assert.throws(()=>validateUri(valid,'other.mongo.cosmos.azure.com'));assert.throws(()=>validateUri(valid.replace('ssl=true','ssl=false'),host));
});

test('the shipped API defaults to rejecting anonymous business requests before data access',async t=>{
 let called=false;const api=createApi({getRepository:async()=>{called=true;throw new Error();}});
 await new Promise(resolve=>api.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>api.close(resolve)));
 const response=await fetch(`http://127.0.0.1:${api.address().port}/api/tenant/requests`);assert.equal(response.status,401);assert.equal(called,false);
});
