/** Validate the caller at every API request. Private networking never bypasses this. */
import {createRemoteJWKSet,jwtVerify} from 'jose';
export class AuthError extends Error { constructor(status){super('Access denied');this.status=status;} }
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function createAuthenticator({tenantId=process.env.AUTH_TENANT_ID,audience=process.env.AUTH_AUDIENCE,allowedClients=(process.env.AUTH_ALLOWED_CLIENT_IDS||'').split(',').filter(Boolean),jwks}={}){
 let keys=jwks;
 return async request=>{
  const authorization=request.headers.authorization;
  if(typeof authorization!=='string'||!/^Bearer [\w.-]+$/.test(authorization)||authorization.length>16384)throw new AuthError(401);
  if(!uuid.test(tenantId||'')||!uuid.test(audience||'')||!allowedClients.length||allowedClients.some(id=>!uuid.test(id)))throw new Error('Authentication configuration missing');
  const issuer=`https://login.microsoftonline.com/${tenantId}/v2.0`;
  keys??=createRemoteJWKSet(new URL(`https://login.microsoftonline.com/${tenantId}/discovery/v2.0/keys`));
  let claims;
  try{({payload:claims}=await jwtVerify(authorization.slice(7),keys,{issuer,audience,algorithms:['RS256'],clockTolerance:5,requiredClaims:['exp','iat','nbf','oid','tid','azp','scp']}));}
  catch{throw new AuthError(401);}
  if(claims.tid!==tenantId||!uuid.test(claims.oid||''))throw new AuthError(401);
  if(!allowedClients.includes(claims.azp)||!String(claims.scp).split(' ').includes('access_as_user'))throw new AuthError(403);
  const roles=Array.isArray(claims.roles)?claims.roles.filter(role=>['Requester','Operator'].includes(role)):[];
  if(!roles.length)throw new AuthError(403);
  return {tenantId,objectId:claims.oid,roles};
 };
}
export function isOperator(actor){return actor.roles.includes('Operator');}
