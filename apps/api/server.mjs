import {createAuthenticator,AuthError} from './auth.mjs';
import {createServer} from 'node:http';
import {pathToFileURL} from 'node:url';
import {repository,dispatch,requestData,publicDocument,ValidationError} from './domain.mjs';
export function createApi({getRepository=repository,publish=dispatch,authenticate=createAuthenticator(),role=process.env.API_ROLE||'all'}={}){
 const allowed=kind=>role==='all'||role===kind;
 const server=createServer(async(req,res)=>{
  const send=(status,value)=>{const data=JSON.stringify(value);res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Content-Length':Buffer.byteLength(data),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(data);};
  const path=new URL(req.url,'http://localhost').pathname;
  if(req.method==='GET'&&path==='/healthz')return send(200,{status:'ok'});
  try{
   const actor=path.startsWith('/api/')?await authenticate(req):null;
   if(req.method==='GET'){
    if(path==='/readyz'){await(await getRepository()).health();return send(200,{status:'ok',database:process.env.USE_IN_MEMORY==='true'?'memory':'cosmos'});}
    if(path==='/api/platform/catalog'&&allowed('platform'))return send(200,{name:'Alba · Portal de solicitudes',categories:['access','maintenance','support'],reference_application:true});
    if(path==='/api/tenant/requests'&&allowed('tenant'))return send(200,{items:await(await getRepository()).list('requests',actor)});
    if(path==='/api/activities/events'&&allowed('activities'))return send(200,{items:await(await getRepository()).list('activities',actor)});
   }
   if(req.method==='POST'&&path==='/api/tenant/requests'&&allowed('tenant')){
    const length=Number(req.headers['content-length']);
    if(req.headers['transfer-encoding']||!Number.isInteger(length)||length<1||length>4096||req.headers['content-type']?.split(';')[0]!=='application/json'){
     res.setHeader('Connection','close');send(400,{error:'Se requiere JSON de hasta 4096 bytes'});req.resume();return;
    }
    const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>4096)throw new TypeError('Body too large');chunks.push(chunk);}
    const data=requestData(JSON.parse(Buffer.concat(chunks).toString('utf8'))),repo=await getRepository(),{document,created}=await repo.create(data,actor);
    try{if(document.outbox_pending)await publish(repo,document);}catch{console.warn('Publicación aplazada; el timer recuperará el outbox');}
    return send(created?202:200,publicDocument(document));
   }
   req.resume();send(404,{error:'Ruta no encontrada'});
  }catch(error){if(error instanceof AuthError){res.setHeader('WWW-Authenticate','Bearer');req.resume();return send(error.status,{error:'Acceso no autorizado'});}if(!res.headersSent)send(error instanceof ValidationError||error instanceof SyntaxError?400:503,{error:error instanceof ValidationError||error instanceof SyntaxError?'Solicitud inválida':'Servicio de datos no disponible'});}
 });
 server.requestTimeout=15000;server.headersTimeout=10000;server.keepAliveTimeout=5000;return server;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const server=createApi();server.listen(Number(process.env.PORT||8000),'0.0.0.0');
 process.on('SIGTERM',()=>server.close(()=>process.exit(0)));
}
