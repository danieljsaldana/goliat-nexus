import {createDiagramViewer} from './diagram-viewer.js';
import {getPublicStars,readStarSnapshot} from './github.js';
import {architectureViews} from './content/architecture-explorer.js';
import {deploymentCommands,deploymentDetails} from './content/deployment-model.mjs';
import {resourceInventory} from './content/resources.js';
import {categories,capabilities,selectCapabilities} from './content/capabilities.js';
import {createStory,advanceStory,recoverStory,duplicateStory,storyData,requestSteps} from './lab.js';
const $=id=>document.getElementById(id);
createDiagramViewer({frame:$('architecture-document'),select:$('diagram-select'),link:$('full-diagram'),loading:$('diagram-loading'),error:$('diagram-error'),retry:$('diagram-retry')});
const spanish=Object.fromEntries([...document.querySelectorAll('[data-i18n]')].map(el=>[el.dataset.i18n,el.innerHTML]));
const english={
'brand.tagline':'MODULAR PLATFORM FOR AZURE',
'stage.edge':'Publish through WAF','stage.edgeText':'Azure hostname and renewable certificate; optional custom domains.','close.edge':'WAF, domains and certificates ↗','close.secrets':'Secrets and rotation ↗','close.versions':'Versions and migration ↗','close.acceptance':'Production criteria ↗','close.modules':'Modules and private agent ↗','nav.platform':'Platform','nav.example':'Example','nav.configure':'Deploy','nav.guide':'Product guide ↗',
'hero.eyebrow':"GOLIAT NEXUS / AZURE APPLICATION PLATFORM",'hero.title':"Your application.<br><em>Its foundation on Azure.</em>",'hero.description':"A modular platform connecting networks, applications and data. Share hub services and deploy Dev and Prod with their own applications, identities and data.",'hero.start':"Explore the solution <span aria-hidden=\"true\">→</span>","hero.note":"Includes Alba: a request application with a Next.js frontend, Node.js APIs and event processing. A reference you can adapt to your project.",
'map.hub':'One hub. Shared resources.','map.once':'×1','map.dev':'Experiment and evolve.','map.prod':'Your own environment.','map.devFoot':'APIs: 0–3 replicas','map.prodFoot':'APIs: 2–5 replicas','map.caption':'Separate data and identities. Shared platform.',
'facts.hub':'shared hub','facts.env':'separate environments',"facts.states":"Terraform states including edge",'facts.flags':'documented capabilities',
'platform.title':"One shared platform.<br>Two spaces to build.","platform.description":"The hub brings together services Dev and Prod need in common. Each environment keeps its own applications and data. Avoid duplicating fixed infrastructure and configure capacity separately.",'platform.shared':'CREATED ONCE',"platform.sharedText":"WAF to publish websites and APIs, Firewall for egress, ACR for images, plus DNS, logs and Terraform state services.",'platform.own':'PER ENVIRONMENT',"platform.ownText":"Separate portals, APIs, Functions, Cosmos and secrets. Two spokes with no direct peering, private access and identity permissions.",'platform.cost':'COST IN CONTEXT','platform.costTitle':'Less duplication.',"platform.costText":"Shared services still incur costs when Dev scales to zero. Budgets send alerts; adjust capacity and retention in your tfvars.",
'diagram.hint':'Open the full view to zoom, move around and inspect each component.','diagram.swaLabel':'FOUR STATIC WEBSITES','diagram.swaTitle':'Two example portals per environment.','diagram.swaText':'The reference creates tenant and admin as independent Azure Static Web Apps in Dev and Prod. These example interfaces can be replaced or adapted to your project. Standard tier, West Europe. HTTPS origins accept the WAF IP only; the portal map can grow.','diagram.agentLabel':'OPTIONAL PRIVATE COMPUTE','diagram.agentTitle':'Your GitHub Actions runner.','diagram.agentText':'An Ubuntu VM in the hub, with NIC, OS disk and system identity. No public IP or inbound GitHub connection. Configure its repository and grant only the permissions required by your workflows.','diagram.guide':'Read the resource and region guide ↗','diagram.select':'Explore the architecture','diagram.open':'Open diagram','diagram.newTab':' (opens in a new tab)','diagram.error':'The diagram could not be loaded. Use the link to open it directly.',
'example.title':"From a request<br>to an activity.",'example.description':"Alba connects two portals, private APIs and a Function. Choose a scenario and watch the request being saved, the event being published and the activity appearing.",'example.simulation':'Local simulation · No deployment or Azure connection','example.portal':'Your workspace','example.views':'Illustrative views. Integrate authentication and authorization before using real data.','example.demoTitle':'From the form to the activity.','example.ready':'Ready to submit','example.send':'Create request','example.activity':'Activity','example.waiting':'Your activity will appear here.','example.outbox':'The outbox supports delivery retries, and the consumer avoids duplicate activities.',"example.private":"Browser \u2192 shared WAF \u2192 web or private gateway \u2192 API. Cosmos, queues and Functions communicate privately; these internal events do not traverse the WAF. The hub also shares Firewall, ACR, DNS and logs.",
'components.title':"The pieces your<br>application needs.",'components.description':"Explore the platform components. Understand their purpose, options and Terraform modules before enabling what you need.",
'secrets.title':"Secrets have a home: Key Vault.",'secrets.text':"APIs and Functions access secrets with their own identity and specific permissions. Cosmos connections never reach the frontend. Synchronization happens outside tfvars; Terraform state needs protection too.",'secrets.guide':'How it works ↗',
'config.title':"Three files.<br>Your own configuration.",'config.description':"Define the shared platform in common.tfvars and each environment’s capacity in dev.tfvars and prod.tfvars. Commented examples help you read, adapt and deploy them.",'config.preset':'Installation','config.source':'View tfvars on GitHub ↗','config.backup':'Periodic backup','config.replicas':'Replicas per API','config.zone':'Container Apps zones','config.requirements':'Terraform ≥1.9, Python, Azure CLI and a subscription session. Applications require a private executor, Node.js ≥24, npm, Linux Docker/Buildx and SWA CLI 2.1.0. Use an existing executor or the optional private VM; configure your own agent repository.','config.copy':'Copy','config.comments':'How the tfvars explain each setting','config.variables':'Read the complete variable guide →',
'inventory.title':"From the map to the code.",'inventory.description':"Explore the modules, inspect reference resources and follow the operations guides. The inventory comes from mock-provider plans, not a bill or a live Azure query.",'inventory.objects':'objects in the full reference configuration','inventory.expand':'View resource types and layers','inventory.stage':'Layer','inventory.resource':'Terraform resource','inventory.quantity':'Count',
'close.title':"Your project is the next step.",'close.text':'Before production: test two Requester users, apply MFA/Conditional Access, rehearse restores, rotation and poison queue recovery, and measure load and costs. Prod Container Apps is zonal; Cosmos remains single-region.','close.manual':'How the product works ↗','close.operations':'Operations and acceptance ↗','footer':'One shared hub. Two environments. A foundation you can understand.','footer.licence':'Noncommercial use'};
Object.assign(english,{
 "story.frontend":"Static Next.js behind the shared WAF. Entra PKCE sign-in and HTTPS API access, without VPN. It never receives Cosmos secrets.",
 "story.backend":"The WAF routes to private Nginx, which calls the Node.js APIs. Each API verifies the token, role and owner before using Cosmos and publishing an event.",
 'story.functions':'Listens to Storage Queue and records one activity per request, even after repeated deliveries. A timer recovers pending outbox messages.',
 'story.choose':'CHOOSE A USE CASE','story.access':'Request access','story.maintenance':'Maintenance','story.support':'Get support',
 'story.scope':'All three use cases register and process requests. Granting access, resolving tickets or executing tasks requires your own business logic.',
 'story.portal':'REQUEST PORTAL','story.play':'Play the full journey','story.next':'Advance one step','story.reset':'Reset',
 'story.failure':'Simulate a failure when publishing to the queue','story.recover':'Recover with the timer Function',
 'story.saved':'requests saved','story.deliveries':'event deliveries','story.activities':'activities recorded',
 'story.duplicate':'Replay the same event','story.payload':'See the data at this step',
 'story.realTitle':'Then check it in your Azure.',
 "story.realText":"Deploy Dev and Prod and publish the edge entry. Then create a request with an assigned Entra user and check its activity. The validation guide distinguishes API checks from the complete browser journey.",
 'story.guide':'Read the full example →',
});
Object.assign(english,{
 'nav.capabilities':'Capabilities','hero.title':"Your application.<br><em>Its foundation on Azure.</em>",
 'hero.description':"A modular platform connecting networks, applications and data. Share hub services and deploy Dev and Prod with their own applications, identities and data.",
 'hero.tag.shared':"Shared hub",'hero.tag.private':"Private data",
 'route.architecture':'The architecture','route.capabilities':'The capabilities','route.example':'A real application','route.configure':'Your deployment',
 'section.architecture':'01 / SHARED ARCHITECTURE','section.capabilities':'02 / EXPLORE THE PRODUCT','section.example':'03 / AN APPLICATION TO UNDERSTAND IT','section.configure':'04 / FROM EXAMPLE TO YOUR AZURE','section.resources':'05 / RESOURCES AND DOCUMENTATION',
 'components.title':"The pieces your<br>application needs.",'components.description':"Explore the platform components. Understand their purpose, options and Terraform modules before enabling what you need.",
 'catalogue.modules':'Explore the Terraform modules ↗','catalogue.search':'Find a capability','catalogue.hint':'Options are defined in each environment’s tfvars.','catalogue.empty':'No matches. Try another term or select the whole product.',
 'compare.label':'ONE FOUNDATION. DIFFERENT CAPACITY.','compare.title':'Dev for iteration.<br>Prod with baseline capacity.','compare.note':'Configurable reference settings, not load-tested sizing. Each environment retains its own data and identities.','compare.caption':'Reference configuration for Dev and Prod','compare.resource':'Configuration','compare.retention':'Cosmos backup retention',
 'security.eyebrow':'SECURITY AT EVERY HOP','security.title':'Private networks.<br>Identity on every request.','security.description':'Zero Trust controls for networking, identity and data access. Being connected to the hub does not grant access to an API or another environment.','security.guide':'Read the security model ↗',
 "security.network":"WAF entry, locked origins","security.networkText":"The WAF inspects public ingress. Static Web Apps accepts only its IP; the internal gateway accepts only its subnet. APIs and data remain private.",'security.identity':'Verified token and role','security.identityText':'Entra with PKCE; the API checks audience, scope, role, tenant and owner.','security.secrets':'Access to the required secret','security.secretsText':'Managed identities and per-secret permissions. No Cosmos connection reaches the frontend.','security.organization':'Your corporate policy','security.organizationText':'Complete MFA, Conditional Access and PIM with your organization. The product does not modify these global policies.',
 'stage.state':'Prepare the state','stage.stateText':'Backend and bootstrap. Close access from a private executor.','stage.shared':'Build the foundation','stage.sharedText':'Shared hub, data, identities and environment services.','stage.dev':'Deploy and verify','stage.devText':'Publish images, Functions and portals; check the flow.','stage.prod':'Apply your capacity','stage.prodText':'The same code, with separate configuration and data for Prod.',
 'guides.eyebrow':'KEEP GOING WITH CONTEXT','guides.title':'From the first deployment to operations.','guides.product':'Understand the product ↗','guides.productText':'Architecture, components and the complete Alba flow.','guides.operations':'Operate and recover ↗','guides.operationsText':'Acceptance, backups, retries and event recovery.','guides.security':'Review security ↗','guides.securityText':'Identity, permissions, private networks and traffic paths.','guides.production':'Prepare for production ↗','guides.productionText':'Acceptance criteria, limits and tests for your installation.',
});

Object.assign(english,{
 'hero.github':"View on GitHub",'hero.try':"Try the Alba journey",
 'scenario.accessTag':'01 / ACCESS','scenario.maintenanceTag':'02 / MAINTENANCE','scenario.supportTag':'03 / SUPPORT',
 'scenario.accessText':'Register a request to join a team workspace.','scenario.maintenanceText':'Register a check for the meeting room equipment.','scenario.supportText':'Register an access issue with the team portal.','scenario.select':'Explore this scenario ↗',
 'scenario.portals':'TWO EXAMPLE PORTALS','scenario.tenant':'User portal','scenario.admin':'Operations portal','scenario.local':'Simulation in your browser',
 'receipt.title':'REQUEST TRACE','receipt.request':'Request','receipt.event':'Event','receipt.activity':'Activity','receipt.note':'One identifier links the document, event and activity.',
 'source.sponsor':'Support development on GitHub Sponsors','source.eyebrow':'CODE TO MAKE YOUR OWN','source.title':"A foundation to start.<br>Code to build on.",'source.text':"Infrastructure, a reference application and documentation in one repository. Replace Alba with your product and keep the pieces that work for you.",'source.open':"View repository on GitHub",'source.modules':'Modular infrastructure','source.docs':'Architecture and operations','source.by':'Created by'
});
Object.assign(english,{
 'diagram.loading':'Preparing the diagram…','diagram.retry':'Retry','diagram.error':'The diagram could not be loaded. Retry or use “Open diagram”. For a local source checkout, build the website with make site first.',
 "topology.label": "Explore the solution",
 "topology.kicker": "INTERACTIVE ARCHITECTURE",
 "topology.hint": "Choose a view and follow how the pieces connect.",
 "related.eyebrow": "ANOTHER GOLIAT PROJECT",
 "related.description": "Explore resources and costs across your Azure subscriptions with an inventory and FinOps dashboard you deploy and manage in your own environment.",
 "related.inventory": "Azure inventory",
 "related.tags": "Tags and costs",
 "related.open": "Explore the tool",
 "topology.shared": "Platform",
 "topology.entry": "Web entry",
 "topology.events": "Events",
 "topology.users": "Users",
 "topology.hub": "Shared hub",
 "topology.own": "Own data",
 "topology.apps": "Portals and APIs",
 "topology.async": "Asynchronous processing",
 "topology.private": "Private access",
 "topology.reference": "Conceptual view · No Azure connection",
 "topology.detail": "View architecture ↗",
 "compare.expand": "Compare Dev and Prod capacity",
 "compare.expandNote": "Replicas · Cosmos · Zones",
 "stack.label": "Infrastructure and application.<br>In one project.",
});
const iconSprite=new URL('./assets/icons.svg',import.meta.url).href;
let capabilityCategory='all',expandedCapabilities=false;
function node(tag,className,value){const el=document.createElement(tag);if(className)el.className=className;if(value)el.textContent=value;return el;}
function renderFilters(){
 $('capability-filters').replaceChildren(...categories.map(([id,label])=>{
  const button=node('button','',label[language]);button.type='button';button.dataset.category=id;button.setAttribute('aria-controls','component-grid');
  button.addEventListener('click',()=>{capabilityCategory=id;expandedCapabilities=false;renderCapabilities();});return button;
 }));
 $('capability-search').placeholder=language==='es'?'Cosmos, agente, presupuesto…':'Cosmos, agent, budget…';
}
function renderCapabilities(){
 const es=language==='es',matches=selectCapabilities(capabilityCategory,$('capability-search').value);
 const featured=new Set(['waf','hub','portals','containers','functions','cosmos']);
 const items=expandedCapabilities?matches:(capabilityCategory==='all'&&!$('capability-search').value.trim()?matches.filter(item=>featured.has(item.id)):matches.slice(0,6));
 const more=$('capability-more');more.hidden=matches.length<=6;more.setAttribute('aria-expanded',expandedCapabilities);more.textContent=expandedCapabilities?(es?'Mostrar menos ↑':'Show fewer ↑'):(es?`Ver las ${matches.length} capacidades ↓`:`View all ${matches.length} capabilities ↓`);
 for(const button of $('capability-filters').querySelectorAll('button'))button.setAttribute('aria-pressed',button.dataset.category===capabilityCategory);
 $('capability-count').textContent=es?`${items.length} de ${capabilities.length} capacidades`:`${items.length} of ${capabilities.length} capabilities`;
 $('capability-empty').hidden=items.length>0;
 const scopes=es?{shared:'Compartido',environment:'Por entorno',optional:'Opcional'}:{shared:'Shared',environment:'Per environment',optional:'Optional'};
 $('component-grid').replaceChildren(...items.map(item=>{
  const article=node('article','component');article.dataset.capability=item.id;
  const top=node('div','component-top'),icon=document.createElementNS('http://www.w3.org/2000/svg','svg');icon.setAttribute('viewBox','0 0 24 24');icon.setAttribute('aria-hidden','true');icon.classList.add('icon');const use=document.createElementNS('http://www.w3.org/2000/svg','use');use.setAttribute('href',iconSprite+'#'+item.icon);icon.append(use);
  const badge=node('span','scope-badge '+item.scope,scopes[item.scope]);top.append(icon,badge);
  const title=node('h3','',item.title[language]),description=node('p','',item.description[language]),points=node('ul','capability-points');
  points.append(...item.points.map(value=>node('li','',value[language])));
  const details=node('details','capability-details'),summary=node('summary','',es?'Recursos y límites':'Resources and limits');details.append(summary,points);
  const settings=node('ul','feature-switches');settings.setAttribute('aria-label',es?'Configuración':'Configuration');
  settings.append(...item.settings.map(value=>{const li=node('li');li.append(node('code','',value));return li;}));
  const link=node('a','capability-guide',es?'Ver funcionamiento ↗':'How it works ↗');link.href='docs/'+item.guide+'.html';link.setAttribute('aria-label',(es?'Ver funcionamiento: ':'How it works: ')+item.title[language]);
  article.append(top,title,description,details,settings,link);return article;
 }));
}
function renderComparison(){
 for(const environment of ['dev','prod']){
  const details=deploymentDetails(catalogue,'product',environment,language),cfg=details.config;
  $('compare-'+environment+'-replicas').textContent=`${cfg.sample.api_min_replicas}–${cfg.sample.api_max_replicas}`;
  $('compare-'+environment+'-cosmos').textContent=details.database;
  $('compare-'+environment+'-backup').textContent=cfg.cosmosdb_config.backup_retention_hours+' h';
  $('compare-'+environment+'-zones').textContent=details.zones;
 }
}
let language='es',profile='dev',preset='product',generation=0;
let topologyView='shared',githubStars=null,githubStarsCheckedAt=null;

function renderTopology(){
 const copy=architectureViews[topologyView][language];
 $('topology').dataset.view=topologyView;
 $('topology').setAttribute('aria-label',language==='es'?'Explorador de la solución':'Solution explorer');
 document.querySelector('.topology-controls').setAttribute('aria-label',language==='es'?'Vista de arquitectura':'Architecture view');
 document.querySelectorAll('[data-topology]').forEach(button=>button.setAttribute('aria-pressed',button.dataset.topology===topologyView));
 for(const key of ['kicker','title','description'])$('topology-'+key).textContent=copy[key];
 $('topology-trace').replaceChildren(...copy.trace.flatMap((label,index)=>{const chip=node('span','',label);chip.style.setProperty('--step',index);if(!index)return [chip];const arrow=node('i','','→');arrow.setAttribute('aria-hidden','true');return [arrow,chip];}));
}
function renderGitHubStars(){
 document.querySelectorAll('[data-github-stars]').forEach(badge=>{
  badge.hidden=githubStars===null;
  if(githubStars===null)return;
  const count=new Intl.NumberFormat(language).format(githubStars);
  badge.querySelector('[data-github-count]').textContent=count;
  badge.setAttribute('aria-label',count+(language==='es'?' estrellas en GitHub':' stars on GitHub'));
  const checked=githubStarsCheckedAt?new Intl.DateTimeFormat(language,{dateStyle:'medium'}).format(new Date(githubStarsCheckedAt)):null;
  badge.title=checked?(language==='es'?`Última comprobación en GitHub: ${checked}`:`Last checked on GitHub: ${checked}`):(language==='es'?'Estrellas consultadas en GitHub':'Star count retrieved from GitHub');
  if(badge.closest('.header-github'))badge.closest('a').setAttribute('aria-label','GitHub · '+count+(language==='es'?' estrellas':' stars'));
 });
}
const topologyMotion=matchMedia('(prefers-reduced-motion: reduce)');
let traceTimer,tracePauseTimer,topologyVisible=false;
function stopTopologyTrace(){
 clearTimeout(traceTimer);clearTimeout(tracePauseTimer);
 $('topology').classList.remove('is-tracing');
}
function startTopologyTrace(){
 stopTopologyTrace();
 if(!topologyVisible||document.hidden||topologyMotion.matches)return;
 const map=$('topology');void map.offsetWidth;map.classList.add('is-tracing');
 traceTimer=setTimeout(()=>{
  map.classList.remove('is-tracing');
  tracePauseTimer=setTimeout(startTopologyTrace,2500);
 },3000);
}
for(const button of document.querySelectorAll('[data-topology]'))button.addEventListener('click',()=>{topologyView=button.dataset.topology;renderTopology();startTopologyTrace();});
const topologyObserver=new IntersectionObserver(entries=>{
 for(const entry of entries){
  const visible=entry.isIntersecting&&entry.intersectionRatio>=.15;
  if(visible!==topologyVisible){topologyVisible=visible;startTopologyTrace();}
 }
},{threshold:[0,.15]});
document.addEventListener('visibilitychange',startTopologyTrace);
topologyMotion.addEventListener('change',startTopologyTrace);
window.addEventListener('pagehide',stopTopologyTrace);
window.addEventListener('pageshow',startTopologyTrace);


try{language=localStorage.getItem('lz-language')==='en'?'en':'es';}catch{}
const catalogue=await fetch(new URL('./content/configuration.json',import.meta.url),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Configuration unavailable');return r.json();});
const diagramViews=await fetch(new URL('./content/diagrams.json',import.meta.url),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Diagrams unavailable');return r.json();});
function updateDiagramText(){
 const select=$('diagram-select'),selected=select.value;
 select.replaceChildren(...diagramViews.map(view=>new Option(view.title[language],view.id)));
 select.value=diagramViews.some(view=>view.id===selected)?selected:diagramViews[0].id;
 const view=diagramViews.find(view=>view.id===select.value);
 $('diagram-description').textContent=view.description[language];
 $('architecture-document').title=view.title[language];
}
function updateInventory(){
 const stage=$('inventory-stage').value,rows=resourceInventory.filter(item=>stage==='all'||item.stage===stage);
 $('resource-rows').replaceChildren(...rows.map(item=>{const tr=document.createElement('tr');for(const value of [item.stage,item.type,item.count]){const td=document.createElement('td');td.textContent=value;tr.append(td);}return tr;}));
 $('inventory-total').textContent=catalogue.presets[preset].total;
}
async function updateProfile(){
 const details=deploymentDetails(catalogue,preset,profile,language),request=++generation;
 $('profile-title').textContent=details.title;$('config-directory').textContent=`${details.directory}/${profile}.tfvars`;
 $('profile-cosmos').textContent=details.database;$('profile-backup').textContent=details.backup;$('profile-replicas').textContent=`${details.config.sample.api_min_replicas}–${details.config.sample.api_max_replicas}`;$('profile-zones').textContent=details.zones;
 $('view-config').href=`${document.querySelector('[data-repository]').href}/tree/main/${details.configurationPath}`;
 for(const name of ['common','dev','prod']) $('file-'+name).href=`${details.directory}/${name}.tfvars`;
 document.querySelectorAll('[data-profile]').forEach(button=>button.setAttribute('aria-pressed',button.dataset.profile===profile));
 $('setup-command').textContent=deploymentCommands(catalogue,preset,profile,language);
 $('verify-example-command').textContent=`./lz verify-application --config ${preset==='demo'?'.local/demo':'.local/environments'} --environment ${profile}`;
 updateInventory();
 try {const response=await fetch(`${details.directory}/${profile}.tfvars`,{cache:'no-store'});if(!response.ok)throw new Error();const text=await response.text();if(request===generation)$('tfvars-preview').textContent=text;}catch{if(request===generation)$('tfvars-preview').textContent=language==='es'?'Consulta los archivos tfvars del repositorio.':'Read the tfvars files in the repository.';}
}
function setLanguage(next){
 language=next;document.documentElement.lang=next;
 document.querySelectorAll('[data-i18n]').forEach(el=>el.innerHTML=(language==='en'?english[el.dataset.i18n]:spanish[el.dataset.i18n])??spanish[el.dataset.i18n]);
 document.querySelectorAll('[data-language]').forEach(button=>button.setAttribute('aria-pressed',button.dataset.language===language));
 $('preset').options[0].text=language==='es'?'Producto':'Product';$('preset').options[1].text=language==='es'?'Demo de evaluación':'Evaluation demo';
 updateDiagramText();
 $('capability-filters').setAttribute('aria-label',language==='es'?'Filtrar capacidades':'Filter capabilities');
 document.querySelector('.page-route').setAttribute('aria-label',language==='es'?'Explorar el producto':'Explore the product');
 document.querySelector('.language').setAttribute('aria-label',language==='es'?'Idioma':'Language');
 $('inventory-stage').setAttribute('aria-label',language==='es'?'Capa':'Layer');
 $('inventory-stage').options[0].text=language==='es'?'Todas las capas':'All layers';
 document.querySelector('.scenario-picker').setAttribute('aria-label',language==='es'?'Casos de ejemplo':'Example scenarios');
 renderFilters();renderCapabilities();renderComparison();renderTopology();renderGitHubStars();
 try{localStorage.setItem('lz-language',language);}catch{} updateProfile();renderStory();
}
for(const button of document.querySelectorAll('[data-language]'))button.addEventListener('click',()=>setLanguage(button.dataset.language));
for(const button of document.querySelectorAll('[data-profile]'))button.addEventListener('click',()=>{profile=button.dataset.profile;updateProfile();});
$('capability-search').addEventListener('input',()=>{expandedCapabilities=false;renderCapabilities();});
$('capability-more').addEventListener('click',()=>{expandedCapabilities=!expandedCapabilities;renderCapabilities();});
$('preset').addEventListener('change',event=>{preset=event.target.value;updateProfile();});
$('inventory-stage').addEventListener('change',updateInventory);
$('diagram-select').addEventListener('change',()=>{updateDiagramText();});
$('copy-command').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('setup-command').textContent);$('copy-command').textContent=language==='es'?'Copiado':'Copied';}catch{$('copy-command').textContent=language==='es'?'Selecciona y copia el bloque':'Select and copy the block';}});
const phaseCopy = {
 es: [
  ['Frontend · Una petición sale del navegador.','Tras iniciar sesión con Entra, Next.js recoge el título y la categoría, crea un UUID y envía JSON con un token de acceso a través del WAF hasta el gateway privado. El navegador no accede a Cosmos ni conoce su conexión.','POST /api/tenant/requests'],
  ['Backend · Valida antes de escribir.','La API Node.js verifica firma, emisor, audiencia, vigencia, cliente, scope y rol del token; después valida el contenido. Un mismo UUID con el mismo contenido identifica la misma solicitud; los secretos se leen de Key Vault con identidad administrada.','requestData → validación de id, title y category'],
  ['Cosmos · La solicitud ya está guardada.','El backend inserta un documento con status=received y outbox_pending=true. Esa marca guarda el trabajo pendiente en el mismo documento, antes de intentar publicar el evento.','requests.insertOne · HTTP 202 Accepted'],
  ['Queue · El backend publica el evento.','La API envía el identificador de la solicitud a requests-events usando identidad administrada. Después limpia la marca del outbox. El mensaje queda listo para que lo consuma la Function.','requests-events · Entra ID · outbox_pending=false'],
  ['Function · Procesa una entrega.','El trigger de cola valida el evento y registra una actividad por su id. Después actualiza la solicitud a processed. Si recibe ese id otra vez, no crea otra actividad.','requestCreated → activities.updateOne + requests.updateOne'],
  ['Frontend · Ahora se puede consultar el resultado.','Al actualizar el portal, el navegador llama a las APIs de solicitudes y actividades. La solicitud aparece procesada y se muestra su actividad. La Function no responde directamente al navegador.','GET /api/tenant/requests + GET /api/activities/events'],
 ],
 en: [
  ['Frontend · A request leaves the browser.','After Entra sign-in, Next.js collects a title and category, creates a UUID and posts JSON with an access token through the WAF to the private gateway. The browser never connects to Cosmos or receives its connection string.','POST /api/tenant/requests'],
  ['Backend · Validate before writing.','The Node.js API verifies token signature, issuer, audience, lifetime, client, scope and role before validating the request. Reusing a UUID with the same content refers to the same request. Managed identity retrieves secrets from Key Vault.','requestData → validate id, title and category'],
  ['Cosmos · The request is already saved.','The backend inserts one document with status=received and outbox_pending=true. That marker stores the pending delivery in the same document, before publishing the event.','requests.insertOne · HTTP 202 Accepted'],
  ['Queue · The backend publishes the event.','The API sends the request identifier to requests-events using managed identity, then clears its outbox flag. The queued message is ready for the Function to consume.','requests-events · Entra ID · outbox_pending=false'],
  ['Function · Process one delivery.','The queue trigger validates the event and upserts an activity by event id, then marks the request processed. Receiving that id again does not create another activity.','requestCreated → activities.updateOne + requests.updateOne'],
  ['Frontend · The result can now be queried.','Refreshing the portal calls the request and activity APIs. It shows the processed request and its activity. The Function does not reply directly to the browser.','GET /api/tenant/requests + GET /api/activities/events'],
 ],
};
let story=createStory(),storyRun=0,storyPlaying=false;
function renderStory(){
 const es=language==='es',data=storyData(story,language);
 $('receipt-id').textContent=data.request.id.slice(0,8)+'…';$('receipt-id').title=data.request.id;
 $('story-progress').value=story.index+1;$('story-progress').setAttribute('aria-label',es?'Progreso del recorrido':'Journey progress');
 $('receipt-request').textContent=story.saved?(es?'Guardada':'Saved'):(story.index>=0?(es?'En curso':'In progress'):(es?'Por enviar':'Not sent'));
 $('receipt-event').textContent=story.published?(es?'Publicado':'Published'):(story.paused?(es?'En outbox':'In outbox'):(es?'Pendiente':'Pending'));
 $('receipt-activity').textContent=story.activities?(es?'Registrada':'Recorded'):(es?'Sin registrar':'Not recorded');
 $('request-title').textContent=data.request.title;
 const statuses=es?{ready:'Preparada para enviar',sent:'Enviada desde el navegador',validated:'Validada por la API',received:'Guardada · Evento pendiente',pending:'Guardada · Publicación fallida',queued:'Evento en cola',processed:'Solicitud procesada'}:{ready:'Ready to submit',sent:'Sent from the browser',validated:'Validated by the API',received:'Saved · Event pending',pending:'Saved · Publishing failed',queued:'Event queued',processed:'Request processed'};
 $('request-state').textContent=statuses[story.status];
 document.querySelectorAll('[data-example]').forEach(button=>{button.classList.toggle('active',button.dataset.example===story.example);button.setAttribute('aria-pressed',button.dataset.example===story.example);});
 requestSteps.forEach((step,index)=>{const item=$('step-'+step);item.className=index<story.index?'done':index===story.index?(story.paused?'current failed':'current'):'';if(index===story.index)item.setAttribute('aria-current','step');else item.removeAttribute('aria-current');});
 let title=es?'Una petición, un identificador.':'One request, one identifier.';
 let description=es?'Avanza un paso o reproduce el recorrido. El mismo UUID enlazará la solicitud, el evento y la actividad. Todos los datos de esta demostración se quedan en tu navegador.':'Advance one step or play the journey. The same UUID links the request, event and activity. All demonstration data stays in your browser.';
 let operation='POST /api/tenant/requests',payload=data.request,label=es?'JSON que enviará el frontend.':'JSON the frontend will send.';
 if(story.index>=0){[title,description,operation]=phaseCopy[language][story.index];}
 if(story.index===2){payload=data.document;label=es?'Documento interno en Cosmos; el outbox no se expone en el portal.':'Internal Cosmos document; the outbox flag is not exposed by the portal.';}
 if(story.index===3){payload=data.event;label=es?'El evento transporta identificadores, no la conexión a la base de datos.':'The event carries identifiers, never database credentials.';}
 if(story.index>=4){payload=data.activity;label=es?'Actividad registrada por la Function, enlazada a la misma solicitud.':'Activity recorded by the Function and linked to the same request.';}
 if(story.paused){title=es?'El envío falla. La solicitud sigue guardada.':'Publishing fails. The request remains saved.';description=es?'No hay mensaje disponible para el trigger de cola, pero outbox_pending continúa en true. La Function de temporizador busca estos documentos cada minuto y reintenta el envío. Pulsa recuperar para continuar con la misma solicitud.':'There is no message for the queue trigger, but outbox_pending remains true. A timer Function finds pending documents every minute and retries delivery. Recover to continue with the same request.';operation='recoverOutbox · timer · 0 */1 * * * *';payload=data.document;label=es?'El documento conserva el trabajo pendiente.':'The document retains the pending work.';}
 else if(story.recovered&&story.index===3){title=es?'El temporizador recupera el evento pendiente.':'The timer recovers the pending event.';description=es?'recoverOutbox publica el mismo id en la cola y limpia su marca. No crea una segunda solicitud. El trigger de cola puede continuar el procesamiento.':'recoverOutbox publishes the same id and clears its marker. It does not create a second request. The queue trigger can continue processing.';operation='recoverOutbox → requests-events';}
 if(story.duplicate){title=es?'Otra entrega. La misma actividad.':'Another delivery. The same activity.';description=es?'La cola puede entregar un evento más de una vez. La Function reutiliza su id y la escritura idempotente mantiene una sola actividad. No se promete una única entrega.':'The queue may deliver an event more than once. The Function reuses its id and the idempotent write retains one activity. Delivery is not guaranteed to happen only once.';operation='activities.updateOne({ id }, { $setOnInsert: … }, { upsert: true })';}
 $('phase-number').textContent=story.index<0?(es?'ANTES DE EMPEZAR':'BEFORE YOU START'):`${es?'PASO':'STEP'} ${story.index+1} / ${requestSteps.length}`;
 $('phase-title').textContent=title;$('phase-description').textContent=description;$('phase-operation').textContent=operation;
 $('payload-label').textContent=label;$('story-json').textContent=JSON.stringify(payload,null,2);
 $('story-saved').textContent=Number(story.saved);$('story-deliveries').textContent=story.deliveries;$('story-activities').textContent=story.activities;
 $('story-recover').hidden=!story.paused;$('story-duplicate').hidden=story.index!==requestSteps.length-1;
 $('story-next').disabled=storyPlaying||story.paused||story.index===requestSteps.length-1;
 $('simulate-request').disabled=story.paused||story.index===requestSteps.length-1;
 $('simulate-request').textContent=storyPlaying?(es?'Pausar recorrido':'Pause journey'):(story.index===requestSteps.length-1?(es?'Recorrido completado':'Journey complete'):(story.index>=0?(es?'Continuar recorrido':'Continue journey'):(es?'Ver el recorrido completo':'Play the full journey')));
 $('story-failure').disabled=story.index>=3||storyPlaying;
}
async function playStory(){
 if(storyPlaying){storyRun++;storyPlaying=false;renderStory();return;}
 const run=++storyRun;storyPlaying=true;
 while(run===storyRun&&!story.paused&&story.index<requestSteps.length-1){
  story=advanceStory(story,{failQueue:$('story-failure').checked});renderStory();
  if(story.paused||story.index===requestSteps.length-1)break;
  await new Promise(resolve=>setTimeout(resolve,2500));
 }
 if(run===storyRun){storyPlaying=false;renderStory();}
}
$('simulate-request').addEventListener('click',playStory);
$('story-next').addEventListener('click',()=>{story=advanceStory(story,{failQueue:$('story-failure').checked});renderStory();});
$('story-reset').addEventListener('click',()=>{storyRun++;storyPlaying=false;story=createStory(story.example);renderStory();});
$('story-recover').addEventListener('click',()=>{story=recoverStory(story);renderStory();});
$('story-duplicate').addEventListener('click',()=>{story=duplicateStory(story);renderStory();});
for(const button of document.querySelectorAll('[data-example]'))button.addEventListener('click',()=>{storyRun++;storyPlaying=false;story=createStory(button.dataset.example);renderStory();document.querySelector('.portal-demo').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});});
$('product-version').textContent='NEXUS · v'+catalogue.version;
$('feature-count').textContent=capabilities.length;
setLanguage(language);
topologyObserver.observe($('topology'));

let publicMetadataStorage=null;
try{publicMetadataStorage=sessionStorage;}catch{}
async function loadGitHubStars(){
 const repository=document.querySelector('[data-repository]').href;
 try{
  const response=await fetch(new URL('./content/github-stars.json',import.meta.url),{cache:'no-store'});
  if(response.ok){
   const snapshot=readStarSnapshot(repository,await response.json());
   if(snapshot){githubStars=snapshot.count;githubStarsCheckedAt=snapshot.checkedAt;renderGitHubStars();}
  }
 }catch{ /* A missing snapshot must not prevent a public GitHub API request. */ }
 const count=await getPublicStars(repository,{storage:publicMetadataStorage});
 if(count!==null){githubStars=count;githubStarsCheckedAt=null;renderGitHubStars();}
}
loadGitHubStars();
