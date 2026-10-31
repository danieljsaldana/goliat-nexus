export function deploymentDetails(catalogue, preset, environment, language = 'es') {
 if (!['product','demo'].includes(preset) || !['dev','prod'].includes(environment)) throw new Error('Unknown preset');
 const data=catalogue.presets[preset],config=data.environments[environment],es=language==='es',db=config.cosmosdb_config;
 return {config,title:`${environment.toUpperCase()} · ${preset==='demo'?'Demo':es?'Producto':'Product'}`,directory:data.directory,
 database:config.enable_cosmosdb ? `MongoDB ${db.mongo_server_version} · ${db.is_serverless?'Serverless':db.max_throughput?`Autoscale ${db.max_throughput} RU/s`:`${db.throughput} RU/s`}` : es?'Desactivado':'Disabled',
 backup:`${db.backup_retention_hours} h · ${es?'intervalo':'interval'} ${db.backup_interval_minutes} min`,
 zones:config.zone_redundancy?(es?'Activada':'Enabled'):(es?'Desactivada':'Disabled'),
 configurationPath:data.directory};
}
export function deploymentCommands(catalogue,preset,environment,language='es') {
 deploymentDetails(catalogue,preset,environment,language);
 const demo=preset==='demo',path=demo?'.local/demo':'.local/environments',es=language==='es';
 return ['az login','',`./lz configure${demo?' --demo':''} \\`,`  --name ${catalogue.presets[preset].name} \\`,`  --operator-ip "${es?'<TU-IP-PUBLICA>/32':'<YOUR-PUBLIC-IP>/32'}" \\`,`  --alert-email "${es?'<TU-CORREO>':'<YOUR-EMAIL>'}" \\`,`  --output-dir ${path}`,'',`# ${es?'Ejecutor Linux privado con sesión del operador, Docker/Buildx y SWA CLI':'Private Linux executor with operator sign-in, Docker/Buildx and SWA CLI'}`,`# ${es?'Un SPN por instalación; cinco planes guardados, aplicados en orden':'One SPN per installation; five saved plans applied in order'}`,`./lz deploy --config ${path} --yes`,'',`# ${es?'Con sesión Entra: prueba por el WAF, sin VPN':'With Entra sign-in: test through the WAF, no VPN'}`,`./lz smoke-test --config ${path} --environment ${environment}`,`./lz verify-application --config ${path} --environment ${environment}`].join('\n');
}
