import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair,exportJWK,SignJWT,createLocalJWKSet} from 'jose';
import {createAuthenticator,AuthError} from '../auth.mjs';
import {MemoryRepository,TENANT,eventFor} from '../domain.mjs';
const audience='66666666-6666-4666-8666-666666666666',client='77777777-7777-4777-8777-777777777777',owner='44444444-4444-4444-8444-444444444444';
const issuer=`https://login.microsoftonline.com/${TENANT}/v2.0`;
const {privateKey,publicKey}=await generateKeyPair('RS256');
const jwks=createLocalJWKSet({keys:[{...await exportJWK(publicKey),kid:'test',alg:'RS256'}]});
const authenticate=createAuthenticator({tenantId:TENANT,audience,allowedClients:[client],jwks});
async function token(extra={},opts={}){return new SignJWT({tid:TENANT,oid:owner,azp:client,scp:'access_as_user',roles:['Requester'],...extra}).setProtectedHeader({alg:'RS256',kid:'test'}).setIssuer(opts.issuer??issuer).setAudience(opts.audience??audience).setIssuedAt().setNotBefore(opts.nbf??'0s').setExpirationTime(opts.exp??'1m').sign(privateKey);}
const request=value=>({headers:{authorization:`Bearer ${value}`}});
test('valid signed Entra-format access token yields a scoped actor',async()=>{
 const actor=await authenticate(request(await token()));assert.equal(actor.objectId,owner);assert.equal(actor.tenantId,TENANT);assert.deepEqual(actor.roles,['Requester']);
});
test('anonymous, expired, wrong issuer/audience/tenant, altered or future tokens are rejected',async()=>{
 await assert.rejects(authenticate({headers:{}}),error=>error instanceof AuthError&&error.status===401);
 for(const value of [await token({}, {exp:'-1m'}),await token({}, {audience:client}),await token({}, {issuer:'https://wrong.example'}),await token({tid:client}),await token({}, {nbf:'1h'})])await assert.rejects(authenticate(request(value)),error=>error.status===401);
 const valid=await token(),parts=valid.split('.');parts[1]=Buffer.from(JSON.stringify({tid:TENANT,oid:owner,roles:['Operator']})).toString('base64url');await assert.rejects(authenticate(request(parts.join('.'))),error=>error.status===401);
});
test('a signed token without the required scope, client or app role grants no data access',async()=>{
 for(const claims of [{roles:[]},{scp:'unrelated'},{azp:owner}])await assert.rejects(authenticate(request(await token(claims))),error=>error.status===403);
});
test('requesters see only their records; operators can operate the configured tenant',async()=>{
 const repo=new MemoryRepository(),a={tenantId:TENANT,objectId:owner,roles:['Requester']},b={...a,objectId:'55555555-5555-4555-8555-555555555555'},operator={...a,roles:['Operator']};
 await repo.create({id:'11111111-1111-4111-8111-111111111111',title:'Owner request',category:'access'},a);
 await repo.create({id:'99999999-9999-4999-8999-999999999999',title:'Other request',category:'support'},b);
 for(const doc of await repo.pending())await repo.process(eventFor(doc));
 assert.equal((await repo.list('requests',a)).length,1);assert.equal((await repo.list('activities',b)).length,1);assert.equal((await repo.list('requests',operator)).length,2);
 await assert.rejects(repo.list('requests',{...a,tenantId:client}));
 await assert.rejects(repo.create({id:'11111111-1111-4111-8111-111111111111',title:'Owner request',category:'access'},b));
 await assert.rejects(repo.process({...eventFor((await repo.pending())[0]),tenant_id:client}));
});
