// A conceptual guide, never a connection to an Azure deployment.
export const architectureViews={
 shared:{
  es:{kicker:'01 / COMPARTIR LA BASE',title:'Se crea una vez. Se usa en los dos entornos.',description:'WAF, Firewall, imágenes, DNS y logs se comparten. Las aplicaciones, los datos y las identidades pertenecen a cada entorno.',trace:['Hub','Dev + Prod']},
  en:{kicker:'01 / SHARE THE FOUNDATION',title:'Created once. Used by both environments.',description:'WAF, Firewall, images, DNS and logs are shared. Each environment owns its applications, data and identities.',trace:['Hub','Dev + Prod']}
 },
 entry:{
  es:{kicker:'02 / PUBLICAR CON CONTROL',title:'Entrada pública. Backend privado.',description:'El navegador accede por HTTPS al WAF. Este publica las webs y llega a las APIs por red privada. Entra autentica; la API valida los permisos.',trace:['Usuario','WAF','Web / API']},
  en:{kicker:'02 / CONTROL PUBLIC ACCESS',title:'Public entry. Private backend.',description:'The browser reaches the WAF over HTTPS. It serves websites and reaches APIs over the private network. Entra authenticates; the API checks permissions.',trace:['User','WAF','Web / API']}
 },
 events:{
  es:{kicker:'03 / PROCESAR EN PRIVADO',title:'La petición continúa como un evento.',description:'La API guarda en Cosmos y publica en Storage Queue. La Function procesa el evento y registra la actividad. Este flujo interno no pasa por el WAF.',trace:['API','Cola','Function','Cosmos']},
  en:{kicker:'03 / PROCESS PRIVATELY',title:'The request continues as an event.',description:'The API writes to Cosmos and publishes to Storage Queue. The Function processes the event and records an activity. This internal flow does not traverse the WAF.',trace:['API','Queue','Function','Cosmos']}
 }
};
