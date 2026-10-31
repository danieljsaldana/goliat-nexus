/** Shared business flow. Cloud failures never fall back to memory. */
export class ValidationError extends TypeError {}
export const TENANT='22222222-2222-4222-8222-222222222222';
function actorFor(actor,tenantId){identifier(actor?.objectId);if(actor?.tenantId!==tenantId||!Array.isArray(actor.roles)||!actor.roles.some(r=>['Requester','Operator'].includes(r)))throw new ValidationError('Invalid actor');return actor;}
function selectorFor(actor,tenantId){actorFor(actor,tenantId);return {tenant_id:tenantId,...(actor.roles.includes('Operator')?{}:{created_by:actor.objectId})};}
export function identifier(value){if(typeof value!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value))throw new ValidationError('Invalid identifier');return value;}
export function requestData(value){
 if(!value||Array.isArray(value)||Object.keys(value).sort().join()!=='category,id,title')throw new ValidationError('Invalid request');
 identifier(value.id);
 if(typeof value.title!=='string'||value.title.trim().length<3||value.title.trim().length>160||/[\u0000-\u001f]/.test(value.title)||!['access','maintenance','support'].includes(value.category))throw new ValidationError('Invalid request');
 return {...value,title:value.title.trim()};
}
export function eventData(value,tenantId){
 if(!value||Array.isArray(value)||Object.keys(value).sort().join()!=='id,request_id,tenant_id,type'||value.tenant_id!==tenantId||value.type!=='request.created')throw new ValidationError('Invalid event');
 identifier(value.id);identifier(value.request_id);if(value.id!==value.request_id)throw new ValidationError('Mismatched event');return value;
}
export function publicDocument({_id,outbox_pending,...document}){return document;}
export function eventFor(document){return {id:document.id,request_id:document.id,tenant_id:document.tenant_id,type:'request.created'};}
function same(old,value){if(!old||old.title!==value.title||old.category!==value.category)throw new ValidationError('Conflicting identifier');return old;}
export class MemoryRepository{
 constructor(tenantId=TENANT){this.tenantId=identifier(tenantId);this.requests=new Map();this.activities=new Map();}
 async health(){return true;}
 async create(value,actor){actorFor(actor,this.tenantId);value=requestData(value);if(this.requests.has(value.id))return {document:structuredClone(same(this.requests.get(value.id)?.created_by===actor.objectId?this.requests.get(value.id):null,value)),created:false};
 const document={...value,tenant_id:this.tenantId,created_by:actor.objectId,created_at:new Date().toISOString(),status:'received',outbox_pending:true};this.requests.set(value.id,document);return {document:structuredClone(document),created:true};}
 async list(collection,actor){const filter=selectorFor(actor,this.tenantId);return [...this[collection].values()].filter(v=>v.tenant_id===filter.tenant_id&&(!filter.created_by||v.created_by===filter.created_by)).sort((a,b)=>b.created_at.localeCompare(a.created_at)).slice(0,50).map(publicDocument);}
 async pending(){return [...this.requests.values()].filter(v=>v.outbox_pending).slice(0,50).map(v=>structuredClone(v));}
 async sent(id){this.requests.get(id).outbox_pending=false;}
 async process(value){const event=eventData(value,this.tenantId),request=this.requests.get(event.request_id);if(!request)throw new ValidationError('Missing request');
 if(!this.activities.has(event.id))this.activities.set(event.id,{id:event.id,request_id:event.request_id,tenant_id:this.tenantId,created_by:request.created_by,created_at:new Date().toISOString(),message:'Solicitud recibida y procesada',type:event.type});request.status='processed';}
}
export function validateUri(uri,host){
 const value=new URL(uri),options=Object.fromEntries([...value.searchParams].map(([k,v])=>[k.toLowerCase(),v.toLowerCase()]));
 if(value.protocol!=='mongodb:'||value.hostname!==host||!host.endsWith('.mongo.cosmos.azure.com')||value.port!=='10255'||!value.username||!value.password||(options.ssl??options.tls)!=='true'||['tlsinsecure','tlsallowinvalidcertificates','tlsallowinvalidhostnames'].some(key=>options[key]==='true'))throw new ValidationError('Invalid Cosmos connection');return uri;
}
async function identity(){const {ManagedIdentityCredential}=await import('@azure/identity');if(!process.env.AZURE_CLIENT_ID)throw new Error('Identity missing');return new ManagedIdentityCredential({clientId:process.env.AZURE_CLIENT_ID});}
export class MongoRepository{
 static async connect(){
  const [{SecretClient},{MongoClient},credential]=await Promise.all([import('@azure/keyvault-secrets'),import('mongodb'),identity()]);
  const secret=await new SecretClient(process.env.KEY_VAULT_URI,credential).getSecret(process.env.COSMOS_SECRET_NAME);
  const client=new MongoClient(validateUri(secret.value,process.env.COSMOS_HOST),{retryWrites:false,tls:true,tlsAllowInvalidCertificates:false,tlsAllowInvalidHostnames:false,serverSelectionTimeoutMS:5000,connectTimeoutMS:5000,socketTimeoutMS:5000,maxPoolSize:10,appName:'alba-requests'});
  try{await client.connect();}catch{await client.close();throw new Error('Database unavailable');}
  return new MongoRepository(client,process.env.COSMOS_DATABASE,identifier(process.env.AUTH_TENANT_ID));
 }
 constructor(client,name,tenantId){this.client=client;this.db=client.db(name);this.tenantId=identifier(tenantId);}
 async health(){await this.client.db('admin').command({ping:1});return true;}
 async create(value,actor){actorFor(actor,this.tenantId);value=requestData(value);const document={...value,_id:value.id,tenant_id:this.tenantId,created_by:actor.objectId,created_at:new Date().toISOString(),status:'received',outbox_pending:true};
  try{await this.db.collection('requests').insertOne(document);return {document,created:true};}
  catch(error){if(error.code!==11000)throw error;const old=await this.db.collection('requests').findOne({_id:value.id,tenant_id:this.tenantId});return {document:same(old?.created_by===actor.objectId?old:null,value),created:false};}
 }
 async list(collection,actor){return (await this.db.collection(collection).find(selectorFor(actor,this.tenantId)).sort({created_at:-1}).limit(50).toArray()).map(publicDocument);}
 async pending(){return this.db.collection('requests').find({tenant_id:this.tenantId,outbox_pending:true}).limit(50).toArray();}
 async sent(id){await this.db.collection('requests').updateOne({_id:id,tenant_id:this.tenantId},{$set:{outbox_pending:false}});}
 async process(value){const event=eventData(value,this.tenantId),selector={_id:event.request_id,tenant_id:this.tenantId};const request=await this.db.collection('requests').findOne(selector);if(!request)throw new ValidationError('Missing request');
  try{await this.db.collection('activities').updateOne({_id:event.id,tenant_id:this.tenantId},{$setOnInsert:{id:event.id,request_id:event.request_id,tenant_id:this.tenantId,created_by:request.created_by,created_at:new Date().toISOString(),message:'Solicitud recibida y procesada',type:event.type}},{upsert:true});}
  catch(error){if(error.code!==11000)throw error;}
  await this.db.collection('requests').updateOne(selector,{$set:{status:'processed'}});
 }
}
let cached,expires=0,connecting;
export async function repository(){
 if(cached&&(process.env.USE_IN_MEMORY==='true'||Date.now()<expires))return cached;
 if(!connecting)connecting=(async()=>{const next=process.env.USE_IN_MEMORY==='true'?new MemoryRepository(identifier(process.env.AUTH_TENANT_ID)):await MongoRepository.connect();const old=cached;cached=next;expires=Date.now()+600000;if(old?.client)setTimeout(()=>old.client.close().catch(()=>{}),60000).unref();return next;})().finally(()=>{connecting=null;});
 return connecting;
}
export async function dispatch(repo,document){
 if(process.env.EVENTS_ENABLED==='false')return false;
 const [{QueueClient},credential]=await Promise.all([import('@azure/storage-queue'),identity()]);
 const event=eventFor(document),queue=new QueueClient(`${process.env.EVENTS_QUEUE_URI.replace(/\/$/,'')}/${process.env.EVENTS_QUEUE_NAME}`,credential);
 await queue.sendMessage(Buffer.from(JSON.stringify(event)).toString('base64'));
 if(process.env.EVENT_GRID_ENDPOINT){
  const {EventGridPublisherClient}=await import('@azure/eventgrid');
  await new EventGridPublisherClient(process.env.EVENT_GRID_ENDPOINT,'EventGrid',credential).send([{id:event.id,subject:`requests/${event.request_id}`,eventType:event.type,eventTime:new Date(),dataVersion:'1.0',data:event}]);
 }
 await repo.sent(document.id);return true;
}
