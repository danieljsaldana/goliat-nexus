import {test} from 'node:test';
import assert from 'node:assert/strict';
import {requestApi,ApiError,apiFailureMessage} from '../apps/portal/lib/api.mjs';
test('a cold read can recover but authentication failures are never retried',async()=>{
 let calls=0;
 const data=await requestApi('https://private.example','/api/tenant/requests','token',{}, {fetcher:async()=>++calls<3?new Response('',{status:503}):Response.json({items:[]}),wait:async()=>{}});
 assert.equal(calls,3);assert.deepEqual(data,{items:[]});
 for(const status of [401,403]){
  calls=0;await assert.rejects(requestApi('https://private.example','/api/tenant/requests','token',{}, {fetcher:async()=>{calls++;return new Response('',{status});},wait:async()=>{}}),error=>error.status===status);
  assert.equal(calls,1);
 }
});
test('an ambiguous POST is not automatically repeated and retains its supplied identifier',async()=>{
 let calls=0;const body=JSON.stringify({id:'11111111-1111-4111-8111-111111111111',title:'Prueba',category:'access'});
 await assert.rejects(requestApi('https://private.example','/api/tenant/requests','token',{method:'POST',body},{fetcher:async(url,options)=>{calls++;assert.equal(options.body,body);throw new TypeError('Failed to fetch');}}),error=>error.code==='network');
 assert.equal(calls,1);assert.match(apiFailureMessage(new ApiError('network'),{write:true}),/conexión.*gateway.*identificador/);
});
test('a private-network failure is distinguished from a response received from the API',async()=>{
 assert.match(apiFailureMessage(new ApiError('http',403)),/permiso/);
 assert.doesNotMatch(apiFailureMessage(new ApiError('http',503)),/VPN/);
 assert.match(apiFailureMessage(new ApiError('http',400)),/datos/);
});
