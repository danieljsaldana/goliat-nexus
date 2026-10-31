import {createHash} from 'node:crypto';
import {parse} from 'parse5';

/** Compute CSP hashes from the HTML script nodes the browser will parse. */
export function inlineScriptHashes(html) {
 const hashes=new Set();
 const nodes=[parse(html)];
 while(nodes.length){
  const node=nodes.pop();
  if(node.tagName==='script'&&!node.attrs.some(attribute=>attribute.name==='src')){
   const text=node.childNodes.map(child=>child.value??'').join('');
   if(text)hashes.add(`'sha256-${createHash('sha256').update(text).digest('base64')}'`);
  }
  nodes.push(...(node.childNodes??[]));
 }
 return [...hashes].sort();
}
