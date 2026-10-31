// Local teaching model. It illustrates the shipped outbox flow; it never calls Azure.
export const requestSteps = ['frontend', 'api', 'cosmos', 'queue', 'function', 'activity'];
export const examples = {
  access: {id:'11111111-1111-4111-8111-111111111111', category:'access', es:'Acceso al espacio de documentación', en:'Access to the documentation workspace'},
  maintenance: {id:'22222222-2222-4222-8222-222222222222', category:'maintenance', es:'Revisar el equipo de la sala de reuniones', en:'Check the meeting room equipment'},
  support: {id:'33333333-3333-4333-8333-333333333333', category:'support', es:'Resolver un problema de acceso al portal', en:'Resolve a portal access issue'},
};
export function createStory(example='access') {
  if(!Object.hasOwn(examples,example)) throw new Error('Unknown example');
  return {example,index:-1,status:'ready',saved:false,published:false,outboxPending:false,paused:false,recovered:false,deliveries:0,activities:0,duplicate:false};
}
export function advanceStory(state,{failQueue=false}={}) {
  if(state.paused || state.index===requestSteps.length-1) return {...state};
  const next={...state,index:state.index+1,duplicate:false};
  switch(requestSteps[next.index]) {
    case 'frontend': next.status='sent'; break;
    case 'api': next.status='validated'; break;
    case 'cosmos': Object.assign(next,{saved:true,outboxPending:true,status:'received'}); break;
    case 'queue':
      if(failQueue) Object.assign(next,{paused:true,status:'pending'});
      else Object.assign(next,{published:true,outboxPending:false,status:'queued'});
      break;
    case 'function': Object.assign(next,{status:'processed',activities:1,deliveries:next.deliveries+1}); break;
    case 'activity': next.status='processed'; break;
  }
  return next;
}
export function recoverStory(state) {
  if(!state.paused || !state.saved || !state.outboxPending) throw new Error('No pending outbox');
  return {...state,paused:false,recovered:true,published:true,outboxPending:false,status:'queued'};
}
export function duplicateStory(state) {
  if(state.index!==requestSteps.length-1 || state.activities!==1) throw new Error('Complete the request first');
  return {...state,deliveries:state.deliveries+1,activities:1,duplicate:true};
}
export function storyData(state,language='es') {
  const value=examples[state.example],id=value.id;
  return {
    request:{id,title:value[language],category:value.category},
    document:state.saved?{id,tenant_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',created_by:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',status:state.activities?'processed':'received',outbox_pending:state.outboxPending}:null,
    event:state.published?{id,request_id:id,tenant_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',type:'request.created'}:null,
    activity:state.activities?{id,request_id:id,type:'request.created',message:'Solicitud recibida y procesada'}:null,
  };
}
