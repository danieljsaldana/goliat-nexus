// Render the checked-in vector artwork; no network or cloud credentials are used.
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {Resvg} from '@resvg/resvg-js';
const root=fileURLToPath(new URL('../',import.meta.url));
for(const name of ['social-card','github-preview']){
 const svg=await readFile(root+`site/assets/${name}.svg`,'utf8');
 const png=new Resvg(svg,{font:{loadSystemFonts:true,defaultFontFamily:'Arial'}}).render().asPng();
 await writeFile(root+`site/assets/${name}.png`,png);
}
const icon=await readFile(root+'site/assets/favicon.svg','utf8');
for(const [name,size] of [['favicon-32',32],['apple-touch-icon',180]]){
 const artwork=size===180?`<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180"><rect width="180" height="180" rx="36" fill="#f0f7ff"/><g transform="translate(27 27) scale(3.15)">${icon.match(/<path[^>]+>/)[0]}</g></svg>`:icon;
 await writeFile(root+`site/assets/${name}.png`,new Resvg(artwork,{fitTo:{mode:'width',value:size}}).render().asPng());
}
console.log('Social cards and app icons rendered locally.');
