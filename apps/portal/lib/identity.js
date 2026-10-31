import {PublicClientApplication} from '@azure/msal-browser';
let ready;
export function initializeIdentity(config){
 if(!config?.auth?.frontend_client_id||!config.auth.tenant_id||!config.auth.scope)throw new Error('Identity configuration missing');
 ready??=(async()=>{
  const app=new PublicClientApplication({auth:{clientId:config.auth.frontend_client_id,authority:`https://login.microsoftonline.com/${config.auth.tenant_id}`,redirectUri:location.origin+(config.base_path||'')+'/redirect/',postLogoutRedirectUri:location.origin+(config.base_path||'')+'/'},cache:{cacheLocation:'sessionStorage'}});
  await app.initialize();const result=await app.handleRedirectPromise();
  const account=result?.account||app.getAllAccounts().find(value=>value.tenantId===config.auth.tenant_id);
  if(account)app.setActiveAccount(account);
  return app;
 })();
 return ready;
}
export async function userToken(app,config){
 const account=app?.getActiveAccount();if(!account)throw new Error('Sign in required');
 try{return(await app.acquireTokenSilent({account,scopes:[config.auth.scope]})).accessToken;}
 catch{await app.acquireTokenRedirect({account,scopes:[config.auth.scope]});throw new Error('Sign in required');}
}
