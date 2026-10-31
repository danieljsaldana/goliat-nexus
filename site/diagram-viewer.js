// The viewer runs independently of configuration and GitHub API requests.
// Relative module URLs work at /, /site/ and a GitHub Pages repository path.
export function createDiagramViewer({frame,select,link,loading,error,retry}){
 let timeout,request=0;
 const finish=success=>{
  clearTimeout(timeout);loading.hidden=true;error.hidden=success;
  frame.setAttribute('aria-busy','false');
 };
 function load(){
  const name=select.value;
  if(!/^[a-z][a-z-]*$/.test(name))return;
  const current=++request,url=new URL(`./diagrams/${name}.html`,import.meta.url);
  link.href=url.href;error.hidden=true;loading.hidden=false;
  frame.title=select.selectedOptions[0].text;frame.setAttribute('aria-busy','true');
  clearTimeout(timeout);
  // Avoid stale generated HTML when switching between local preview builds.
  url.search=new URLSearchParams({theme:'light',present:'1',v:String(Date.now())});
  frame.onload=()=>{
   if(current!==request)return;
   try{
    if(frame.contentWindow.location.href!==url.href)return;
    // A 200 SPA fallback or a 404 page must not be mistaken for a diagram.
    finish(Boolean(frame.contentDocument.querySelector('svg[aria-labelledby="archify-diagram-title archify-diagram-description"] [data-node-id]')));
   }catch{finish(false);}
  };
  frame.onerror=()=>{if(current===request)finish(false);};
  timeout=setTimeout(()=>{if(current===request)finish(false);},15000);
  frame.loading='eager';frame.src=url.href;
 }
 select.addEventListener('change',load);retry.addEventListener('click',load);
 load();return {load};
}
