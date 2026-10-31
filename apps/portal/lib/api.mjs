export class ApiError extends Error {
 constructor(code,status=0){super(code);this.name='ApiError';this.code=code;this.status=status;}
}

// Only reads may retry. A write keeps its UUID and requires an explicit retry.
export async function requestApi(gateway,path,token,options={},dependencies={}){
 if(!gateway)throw new ApiError('configuration');
 const fetcher=dependencies.fetcher??globalThis.fetch;
 const wait=dependencies.wait??(ms=>new Promise(resolve=>setTimeout(resolve,ms)));
 const read=['GET','HEAD'].includes((options.method??'GET').toUpperCase());
 const attempts=read?6:1;
 for(let attempt=0;attempt<attempts;attempt++){
  let failure;
  try{
   const response=await fetcher(gateway+path,{...options,headers:{...options.headers,Authorization:`Bearer ${token}`},signal:AbortSignal.timeout(15000)});
   if(response.ok){try{return await response.json();}catch{throw new ApiError('response');}}
   failure=new ApiError('http',response.status);
  }catch(error){
   failure=error instanceof ApiError?error:new ApiError(['AbortError','TimeoutError'].includes(error.name)?'timeout':'network');
  }
  const transient=failure.code==='timeout'||[502,503,504].includes(failure.status);
  if(!read||!transient||attempt===attempts-1)throw failure;
  dependencies.onRetry?.();await wait(3000);
 }
}

export function apiFailureMessage(error,{write=false}={}){
 let message;
 if(error.code==='network')message='No se puede conectar con la API. Comprueba la conexión y la disponibilidad del gateway.';
 else if(error.code==='timeout')message='La API no ha respondido a tiempo. Puede estar arrancando; espera y pulsa Actualizar.';
 else if(error.code==='identity'||error.status===401)message='La sesión no permite acceder a la API. Vuelve a iniciar sesión con Microsoft.';
 else if(error.status===403)message='Tu cuenta no tiene permiso para esta operación. Revisa las asignaciones de Entra del entorno.';
 else if(error.status===400)message='La API ha rechazado los datos. Revisa el título y la categoría de la solicitud.';
 else if([502,503,504].includes(error.status))message='El servicio no está disponible o está arrancando. Espera y pulsa Actualizar.';
 else if(error.code==='configuration')message='El gateway no está configurado. Revisa la publicación del portal.';
 else message='La API no ha devuelto una respuesta válida. Revisa el estado del servicio.';
 return write?message+' Se conserva el identificador: al reintentar el mismo contenido no se duplica la solicitud.':message;
}
