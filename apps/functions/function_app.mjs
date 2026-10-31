import {app} from '@azure/functions';
import {repository,dispatch} from './domain.mjs';
import {processEvent,recoverOutbox} from './handlers.mjs';
app.storageQueue('requestCreated',{queueName:'requests-events',connection:'Events',handler:async(message,context)=>{
 try{await processEvent(message,await repository());}
 catch{context.error('Event processing failed; retry or poison queue.');throw new Error('Event processing failed');}
}});
app.timer('recoverOutbox',{schedule:'0 */1 * * * *',runOnStartup:false,useMonitor:true,handler:async(timer,context)=>{
 try{await recoverOutbox(await repository(),dispatch);}
 catch{context.error('Outbox recovery deferred until the next interval.');throw new Error('Outbox recovery failed');}
}});
