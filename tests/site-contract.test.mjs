import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {deploymentCommands,deploymentDetails} from '../site/content/deployment-model.mjs';
const data=JSON.parse(readFileSync(new URL('../site/content/configuration.json',import.meta.url)));
test('product and demo use distinct deployment identities and paths',()=>{
 for(const environment of ['dev','prod']){
 const product=deploymentCommands(data,'product',environment),demo=deploymentCommands(data,'demo',environment);
 assert.doesNotMatch(product,/--demo|psql/);assert.match(product,/\.local\/environments/);assert.match(demo,/configure --demo/);assert.match(demo,/\.local\/demo/);
 assert.notEqual(data.presets.product.name,data.presets.demo.name);
 assert.equal(product.split('\n').filter(line=>line.startsWith('./lz deploy ')).length,1);
 assert.match(product,/\.\/lz deploy --config \.local\/environments --yes/);
 }
});
test('Cosmos settings and optional flags follow real exported tfvars',()=>{
 const changed=structuredClone(data);changed.presets.product.environments.prod.cosmosdb_config.throughput=800;
 assert.match(deploymentDetails(changed,'product','prod').database,/800 RU/);
 changed.presets.product.environments.prod.enable_cosmosdb=false;
 assert.equal(deploymentDetails(changed,'product','prod').database,'Desactivado');
 assert.throws(()=>deploymentDetails(data,'unknown','dev'));
});
