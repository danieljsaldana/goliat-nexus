/** Build a small, locally served Lucide sprite from the pinned package. */
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const manifest=JSON.parse(await readFile(resolve(root,'site/content/icons.json'),'utf8'));
const library=resolve(root,'node_modules/lucide-static');
const pkg=JSON.parse(await readFile(resolve(library,'package.json'),'utf8'));
if(pkg.version!==manifest.version)throw Error('Run npm ci: Lucide version differs from the icon manifest.');
const symbols=[];
for(const [id,name] of Object.entries(manifest.icons)){
 if(!/^[a-z][a-z0-9-]*$/.test(id)||!/^[a-z][a-z0-9-]*$/.test(name))throw Error('Invalid icon identifier');
 const svg=await readFile(resolve(library,'icons',name+'.svg'),'utf8');
 const content=svg.match(/<svg\b[^>]*>([\s\S]*?)<\/svg>/)?.[1];
 if(!content||/<(?:script|foreignObject)\b/i.test(content))throw Error('Unexpected icon content: '+name);
 symbols.push(`<symbol id="${id}" viewBox="0 0 24 24">${content.trim()}</symbol>`);
}
await writeFile(resolve(root,'site/assets/icons.svg'),`<!-- Lucide ${pkg.version} · ISC/MIT · See Lucide-LICENSE.txt -->\n<svg xmlns="http://www.w3.org/2000/svg">\n${symbols.join('\n')}\n</svg>\n`);
await writeFile(resolve(root,'site/assets/Lucide-LICENSE.txt'),await readFile(resolve(library,'LICENSE')));
console.log(`Built ${symbols.length} Lucide icons (${pkg.version}) for local hosting.`);
