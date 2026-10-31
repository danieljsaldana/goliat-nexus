/** Pure handlers for the Azure triggers, shared with local end-to-end tests. */
import {eventData} from './domain.mjs';
export async function processEvent(message,repo){
 const value=typeof message==='string'?JSON.parse(message):message;
 await repo.process(eventData(value,repo.tenantId));
}
export async function recoverOutbox(repo,publish){for(const doc of await repo.pending())await publish(repo,doc);}
