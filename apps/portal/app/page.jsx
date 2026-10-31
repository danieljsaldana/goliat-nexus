'use client';
import {useEffect,useRef,useState} from 'react';
import {initializeIdentity,userToken} from '../lib/identity';
import {requestApi,ApiError,apiFailureMessage} from '../lib/api.mjs';
const labels={received:'RECIBIDA · PENDIENTE DE EVENTO',processed:'PROCESADA'};
export default function Portal(){
 const [config,setConfig]=useState(null),[connection,setConnection]=useState('Comprobando conexión…'),[items,setItems]=useState([]),[activities,setActivities]=useState([]),[busy,setBusy]=useState(false),[sending,setSending]=useState(false),[result,setResult]=useState(''),[title,setTitle]=useState(''),[category,setCategory]=useState('access');
 const pending=useRef(null),identity=useRef(null);
 const [account,setAccount]=useState(null),[authReady,setAuthReady]=useState(false),[canSubmit,setCanSubmit]=useState(false);
 async function api(cfg,path,options){
  let token;try{token=await userToken(identity.current,cfg);}catch{throw new ApiError('identity');}
  return requestApi(cfg.gateway,path,token,options,{onRetry:()=>setConnection('Esperando a que arranque la API… Las lecturas se reintentan; no se reenvían solicitudes automáticamente.')});
 }
 async function refresh(cfg=config){
  if(!cfg)return;setBusy(true);
  try{
   if(!cfg.features.enable_api_tenant&&!cfg.features.enable_api_activities){setCanSubmit(false);setConnection('Las APIs de solicitudes y actividades están desactivadas en este entorno.');return;}
   await Promise.all([
    cfg.features.enable_api_tenant?api(cfg,'/api/tenant/requests').then(data=>setItems(data.items)):null,
    cfg.features.enable_api_activities?api(cfg,'/api/activities/events').then(data=>setActivities(data.items)):null,
   ]);
   setCanSubmit(true);setConnection('Conexión con las APIs disponible. Actualiza para seguir el procesamiento.');
  }catch(error){setCanSubmit(false);setConnection(apiFailureMessage(error));}
  finally{setBusy(false);}
 }
 useEffect(()=>{let active=true;
  (async()=>{
   const response=await fetch((process.env.NEXT_PUBLIC_BASE_PATH||'')+'/config.json',{cache:'no-store'});if(!response.ok)throw new Error();const cfg=await response.json();if(!active)return;setConfig(cfg);
   if(!cfg.auth){setConnection('Identidad no configurada: despliega la plataforma y publica la configuración del portal. Las APIs permanecen protegidas.');return;}
   const app=await initializeIdentity(cfg);if(!active)return;identity.current=app;setAuthReady(true);const current=app.getActiveAccount();setAccount(current);
   if(current)await refresh(cfg);else setConnection('Inicia sesión con tu cuenta de Microsoft Entra para consultar o crear solicitudes.');
  })().catch(()=>{if(active)setConnection('No se pudo preparar el acceso. Revisa la configuración de identidad y las asignaciones de Entra.');});
  return()=>{active=false;};
 },[]);
 async function login(){try{await identity.current.loginRedirect({scopes:[config.auth.scope],prompt:'select_account'});}catch{setConnection('No se pudo iniciar sesión. Revisa el acceso asignado a esta aplicación.');}}
 async function logout(){setCanSubmit(false);setItems([]);setActivities([]);setAccount(null);setResult('');try{await identity.current.logoutRedirect();}catch{setConnection('Cierra esta pestaña y vuelve a abrir el portal para completar la salida.');}}
 async function submit(event){
  event.preventDefault();if(!canSubmit||busy||sending)return;setSending(true);
  const payload={title:title.trim(),category};
  if(!pending.current||pending.current.payload!==JSON.stringify(payload))pending.current={id:crypto.randomUUID(),payload:JSON.stringify(payload)};
  try{const saved=await api(config,'/api/tenant/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,id:pending.current.id})});setResult(`Recibida · ${saved.id.slice(0,8)}. La Function registrará su actividad.`);pending.current=null;setTitle('');setCategory('access');await refresh();}
  catch(error){setResult(apiFailureMessage(error,{write:true}));}
  finally{setSending(false);}
 }
 const writable=account&&config&&config.features.enable_api_tenant;
 return <><header><a className="brand" href={(process.env.NEXT_PUBLIC_BASE_PATH||'')+'/'}><svg viewBox="0 0 32 32" aria-hidden="true"><path fill="#46cfb1" d="m16 2 14 27H2z"/><path fill="#102c3b" d="m16 12 6 12H10z"/></svg>alba<span>solicitudes</span></a><span className="pill">{config?`${config.environment.toUpperCase()} · ${config.evaluation?'Evaluación':'Referencia'}`:'Aplicación de referencia'}</span></header>
 <main><section className="intro"><p className="eyebrow">{config?`PORTAL ${config.role.toUpperCase()} · SOLICITUDES`:'UN ESPACIO PARA RESOLVER'}</p><h1>De una petición<br/>a una solución.</h1><p>Centraliza las solicitudes de acceso, mantenimiento y soporte. Sigue cada paso, desde la recepción hasta su procesamiento.</p><div className="steps"><span>01 · Solicitud</span><i>→</i><span>02 · Evento</span><i>→</i><span>03 · Actividad</span></div></section>
 <div className="notice">Aplicación de referencia: frontend Next.js estático, backend privado y Azure Functions. El acceso usa Microsoft Entra: cada solicitante ve sus propios registros y los operadores autorizados gestionan el entorno. La red privada y las identidades administradas añaden protección a los servicios.</div>
 <div className="identity-panel">{account?<><span>Sesión de Microsoft Entra activa</span><button className="secondary" onClick={logout}>Cerrar sesión</button></>:<><span>Solo usuarios y grupos asignados a esta aplicación.</span><button disabled={!authReady} onClick={login}>Iniciar sesión con Microsoft</button></>}</div>
 <div id="connection" role="status" data-connected={canSubmit}>{connection}</div>
 <div className="workspace"><section className="panel"><p className="eyebrow">HAZ QUE OCURRA</p><h2>Una nueva solicitud</h2>{writable?<form onSubmit={submit}><label htmlFor="title">¿Qué necesitas?</label><input id="title" minLength={3} maxLength={160} placeholder="Acceso al espacio de documentación" value={title} onChange={e=>setTitle(e.target.value)} required/><label htmlFor="category">Tipo de solicitud</label><select id="category" value={category} onChange={e=>setCategory(e.target.value)}><option value="access">Acceso</option><option value="maintenance">Mantenimiento</option><option value="support">Soporte</option></select><button disabled={sending||busy||!canSubmit} aria-describedby="connection" type="submit">{sending?'Enviando…':'Enviar solicitud'} <span aria-hidden="true">↗</span></button><p className="hint">Pulsa Actualizar para comprobar la conexión y habilitar el envío. El identificador se conserva al reintentar el mismo contenido.</p></form>:<p className="hint">Inicia sesión para crear una solicitud. Los permisos se comprueban en la API, aunque abras otra vista del portal.</p>}<p id="result" role="status">{result}</p></section>
 <section className="panel queue"><div className="panel-heading"><div><p className="eyebrow">EN MARCHA</p><h2>Últimas solicitudes</h2></div><button className="secondary" type="button" disabled={busy||!account} onClick={()=>refresh()}>Actualizar</button></div><ol>{items.length?items.map(item=><li key={item.id}><strong>{item.title}</strong><small>{new Date(item.created_at).toLocaleString('es-ES')} · {item.id.slice(0,8)}</small><span className="status">{labels[item.status]||item.status}</span></li>):<li className="empty">{canSubmit?'Todavía no hay solicitudes disponibles.':'Inicia sesión y comprueba la conexión para consultar las solicitudes.'}</li>}</ol></section></div>
 <section className="panel activities"><p className="eyebrow">LO QUE VA SUCEDIENDO</p><h2>Actividad del procesador</h2><p className="hint">La Function recoge los eventos de la cola y guarda la actividad en Cosmos DB.</p><ol>{activities.length?activities.map(item=><li key={item.id}><strong>{item.message}</strong><small>{new Date(item.created_at).toLocaleString('es-ES')} · {item.id.slice(0,8)}</small></li>):<li className="empty">{canSubmit?'Las actividades aparecerán aquí cuando se procese una solicitud.':'Las actividades se consultarán cuando haya conexión con la API.'}</li>}</ol></section><footer><span>alba · Frontend Next.js estático</span><span>Cosmos DB · Storage Queue · Azure Functions</span></footer></main></>;
}
