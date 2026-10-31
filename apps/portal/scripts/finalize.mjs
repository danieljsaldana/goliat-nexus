import {readdir,readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
async function files(dir){const entries=await readdir(dir,{withFileTypes:true});return(await Promise.all(entries.map(e=>e.isDirectory()?files(join(dir,e.name)):[join(dir,e.name)]))).flat();}
const hashes=new Set();
for(const file of await files('out')){
 if(!file.endsWith('.html'))continue;
 const html=await readFile(file,'utf8');
 for(const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){
  if(/\bsrc\s*=/.test(match[1])||!match[2])continue;
  hashes.add(`'sha256-${createHash('sha256').update(match[2]).digest('base64')}'`);
 }
}
const config={navigationFallback:{rewrite:'/index.html',exclude:['/config.json','/_next/*','/redirect/*','/*.{js,css,svg,ico,png}']},globalHeaders:{'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':`default-src 'self'; script-src 'self' ${[...hashes].join(' ')}; style-src 'self'; connect-src 'self' https://*.azurecontainerapps.io https://login.microsoftonline.com; frame-src 'self' https://login.microsoftonline.com; frame-ancestors 'none'; base-uri 'none'`}};
config.routes=[{route:'/redirect/*',headers:{'Content-Security-Policy':config.globalHeaders['Content-Security-Policy'].replace("frame-ancestors 'none'","frame-ancestors 'self'")}}];
await writeFile('out/staticwebapp.config.json',JSON.stringify(config,null,2)+'\n');
console.log('Static export ready: out/ with CSP hashes and no server runtime.');
