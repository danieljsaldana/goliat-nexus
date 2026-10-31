import http from 'node:http';
import {X509Certificate,randomUUID} from 'node:crypto';
import {promisify} from 'node:util';
import {execFile} from 'node:child_process';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import acme from 'acme-client';
import {ManagedIdentityCredential} from '@azure/identity';
import {SecretClient} from '@azure/keyvault-secrets';
import {CertificateClient} from '@azure/keyvault-certificates';
import {BlockBlobClient} from '@azure/storage-blob';
const run=promisify(execFile),tokens=new Map();
const hosts=JSON.parse(process.env.CERTIFICATE_HOSTNAMES||'[]');
if(!hosts.length||hosts.some(h=>!/^[a-z0-9.-]+$/.test(h)))throw new Error('Invalid certificate hostnames');
const credential=new ManagedIdentityCredential({clientId:process.env.AZURE_CLIENT_ID});
const secrets=new SecretClient(process.env.KEY_VAULT_URI,credential),certificates=new CertificateClient(process.env.KEY_VAULT_URI,credential);
const lock=new BlockBlobClient(process.env.LOCK_BLOB_URL,credential);
const name='waf-tls';let running=false,lastSuccess=null;
// A single public HTTP-01 path; no issuance, key or management API is exposed.
http.createServer((req,res)=>{
 const path=new URL(req.url,'http://localhost').pathname;
 res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Cache-Control','no-store');
 if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);return res.end();}
 if(path==='/healthz'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({status:'ok'}));}
 const match=/^\/.well-known\/acme-challenge\/([A-Za-z0-9_-]{20,512})$/.exec(path);
 if(match&&tokens.has(match[1])){res.setHeader('Content-Type','text/plain');return res.end(tokens.get(match[1]));}
 if(path==='/'){
  const portals=JSON.parse(process.env.PUBLIC_PORTALS||'{}');
  res.setHeader('Content-Type','text/html; charset=utf-8');
  res.setHeader('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'");
  return res.end(`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Goliat - Nexus · Alba</title><style>body{font:18px/1.6 system-ui;background:#101f2b;color:#e8f3f7;max-width:850px;margin:10vh auto;padding:24px}h1{font-size:clamp(40px,8vw,72px);line-height:1.1}a{display:inline-block;margin:12px 16px 12px 0;padding:14px 22px;background:#74e4c3;color:#102b2e;border-radius:12px;text-decoration:none}small{color:#9db8c7}section{border-top:1px solid #37505c;padding:22px 0}</style><small>GOLIAT - NEXUS · APLICACIÓN DE REFERENCIA</small><h1>Una solicitud.<br>Todo conectado.</h1><p>Frontend Next.js, APIs Node.js y procesamiento de eventos. Acceso mediante Microsoft Entra.</p>${Object.entries(portals).map(([env,entries])=>`<section><h2>${env.toUpperCase()}</h2>${Object.entries(entries).map(([portal,url])=>`<a href="${url}">${portal==='admin'?'Portal de administración':portal==='tenant'?'Portal de solicitudes':portal}</a>`).join('')}</section>`).join('')}<small>Entrada HTTPS protegida por WAF. Datos y procesamiento en red privada.</small></html>`);
 }
 res.writeHead(404);res.end();
}).listen(8080,'0.0.0.0');
async function renew(){
 if(running)return;running=true;let lease,heartbeat,lost=false;
 try{
  try{await lock.upload('',0,{conditions:{ifNoneMatch:'*'}});}catch(e){if(![409,412].includes(e.statusCode))throw e;}
  lease=lock.getBlobLeaseClient(randomUUID());
  try{await lease.acquireLease(60);}catch(e){if(e.statusCode===409)return;throw e;}
  heartbeat=setInterval(()=>lease.renewLease().catch(()=>{lost=true;}),25000);
  const current=await certificates.getCertificate(name).catch(e=>{if(e.statusCode===404)return null;throw e;});
  if(current?.cer){
   const cert=new X509Certificate(current.cer);
   if(cert.issuer!==cert.subject&&Date.parse(cert.validTo)-Date.now()>20*86400000&&hosts.every(h=>cert.checkHost(h))){lastSuccess=new Date().toISOString();return;}
  }
  const testToken=randomUUID().replaceAll('-','')+randomUUID().replaceAll('-','');tokens.set(testToken,testToken);
  try{
   for(const hostname of hosts){
    const response=await fetch(`http://${hostname}/.well-known/acme-challenge/${testToken}`,{signal:AbortSignal.timeout(10000),redirect:'error'});
    if(!response.ok||await response.text()!==testToken)throw new Error('WAF HTTP-01 route not ready');
   }
  }finally{tokens.delete(testToken);}
  let key;
  try{key=(await secrets.getSecret('acme-account-key')).value;}catch(e){if(e.statusCode!==404)throw e;}
  if(!key){key=(await acme.crypto.createPrivateKey()).toString();await secrets.setSecret('acme-account-key',key);}
  const client=new acme.Client({directoryUrl:process.env.ACME_DIRECTORY_URL,accountKey:key});
  const [privateKey,csr]=await acme.crypto.createCsr({commonName:hosts[0],altNames:hosts});
  const chain=await client.auto({csr,email:process.env.ACME_EMAIL,termsOfServiceAgreed:true,challengePriority:['http-01'],skipChallengeVerification:true,
   challengeCreateFn:async(_auth,challenge,keyAuthorization)=>{tokens.set(challenge.token,keyAuthorization);},
   challengeRemoveFn:async(_auth,challenge)=>{tokens.delete(challenge.token);}});
  if(lost)throw new Error('Certificate lease lost');
  const folder=await mkdtemp(join(tmpdir(),'nexus-tls-'));
  try{
   await writeFile(join(folder,'key.pem'),privateKey,{mode:0o600});await writeFile(join(folder,'chain.pem'),chain,{mode:0o600});
   await run('openssl',['pkcs12','-export','-out',join(folder,'cert.pfx'),'-inkey',join(folder,'key.pem'),'-in',join(folder,'chain.pem'),'-passout','pass:']);
   await certificates.importCertificate(name,await readFile(join(folder,'cert.pfx')),{tags:{ManagedBy:'Goliat-Nexus',Issuer:'ACME'}});
   lastSuccess=new Date().toISOString();console.log(JSON.stringify({event:'certificate-renewed',hostnames:hosts,at:lastSuccess}));
  }finally{await rm(folder,{recursive:true,force:true});}
 }catch(e){console.error(JSON.stringify({event:'certificate-renewal-failed',code:e.code||e.statusCode||e.name,message:String(e.message).slice(0,300)}));}
 finally{if(heartbeat)clearInterval(heartbeat);if(lease)await lease.releaseLease().catch(()=>{});tokens.clear();running=false;}
}
// Retry bootstrap while App Gateway is being provisioned; then keep renewing before expiry.
if(process.env.RENEW_ENABLED!=='false')setTimeout(()=>{renew();setInterval(renew,2*60*1000);},15000);
