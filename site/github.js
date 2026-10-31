// Public repository metadata only. No token, cookies or authenticated API calls.
export async function getPublicStars(repository, {fetcher=globalThis.fetch, storage=null, now=Date.now, timeoutMs=4000}={}) {
  let url;
  try { url=new URL(repository); } catch { return null; }
  const match=url.pathname.match(/^\/([\w-]+)\/([\w.-]+)\/?$/);
  if(url.origin!=='https://github.com'||url.username||url.password||url.search||url.hash||!match)return null;
  const name=match.slice(1).join('/'),key='nexus:github-stars:'+name;
  const valid=value=>value===null||(Number.isSafeInteger(value)&&value>=0);
  try {
    const cached=JSON.parse(storage?.getItem(key)??'null');
    if(cached&&valid(cached.count)&&Number.isFinite(cached.at)&&cached.at<=now()&&now()-cached.at<(cached.count===null?300000:900000))return cached.count;
  } catch { /* Storage may be unavailable or contain an old value. */ }
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
  let count=null;
  try {
    const response=await fetcher('https://api.github.com/repos/'+name,{
      headers:{Accept:'application/vnd.github+json'},credentials:'omit',referrerPolicy:'no-referrer',signal:controller.signal
    });
    if(response.ok){
      const data=await response.json();
      if(data.private===false&&data.full_name?.toLowerCase()===name.toLowerCase()&&Number.isSafeInteger(data.stargazers_count)&&data.stargazers_count>=0)count=data.stargazers_count;
    }
  } catch { /* Private, offline, rate limited or timed out: retain the plain GitHub link. */ }
  finally { clearTimeout(timer); }
  try { storage?.setItem(key,JSON.stringify({count,at:now()})); } catch { /* No storage is required. */ }
  return count;
}

// A verified, dated snapshot keeps static/private previews useful without tokens.
export function readStarSnapshot(repository,snapshot){
 if(snapshot?.repository!==repository||!Number.isSafeInteger(snapshot.count)||snapshot.count<0)return null;
 const checked=Date.parse(snapshot.checked_at);
 if(!Number.isFinite(checked)||checked>Date.now()+300000)return null;
 return {count:snapshot.count,checkedAt:snapshot.checked_at};
}
