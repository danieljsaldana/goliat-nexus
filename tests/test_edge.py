import copy
import json
import tempfile
import unittest
from pathlib import Path
from product.config import ConfigError,normalize
from product.edge import swa_configuration,check_public_plan
from product import operations
from types import SimpleNamespace
from unittest.mock import patch
from test_product import raw_config

class PublicEntryTests(unittest.TestCase):
    def test_public_mode_rejects_an_origin_that_cannot_be_locked_down(self):
        data=raw_config();data['public_entrypoint']['enabled']=True
        data['environments']['dev']['web']['sku']='Free'
        with self.assertRaisesRegex(ConfigError,'Standard'):normalize(data)

    def test_hostname_configuration_rejects_urls_wildcards_and_paths(self):
        for value in ('https://apps.example.org','*.example.org','apps.example.org/path','apps.example.org:443'):
            data=raw_config();data['public_entrypoint']['hostname']=value
            with self.subTest(value=value),self.assertRaises(ConfigError):normalize(data)
        data=raw_config();data['public_entrypoint']['environment_hostnames']={'dev':'dev.tenant.test','prod':'prod.tenant.test'}
        self.assertNotEqual(normalize(data)['public_entrypoint']['environment_hostnames']['dev'],'')

    def test_static_origin_allows_only_waf_address_and_hashes_inline_script(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'index.html').write_text('<script>console.log("boot")</script>')
            cfg=swa_configuration('8.8.8.8',folder,'/dev/tenant')
        self.assertEqual(cfg['networking']['allowedIpRanges'],['8.8.8.8/32'])
        self.assertIn("'sha256-",cfg['globalHeaders']['Content-Security-Policy'])
        self.assertNotIn("script-src 'self' 'unsafe-inline'",cfg['globalHeaders']['Content-Security-Policy'])
        self.assertEqual(cfg['routes'][0]['route'],'/dev/tenant/config.json')

    def plan(self):
        gateway={'sku':[{'name':'WAF_v2'}],'backend_http_settings':[{'protocol':'Https','port':443,'certificate_chain_validation_enabled':True,'sni_validation_enabled':True}], 'ssl_certificate':[{'key_vault_secret_id':'https://vault.vault.azure.net/secrets/tls','data':None}]}
        return {'planned_values':{'root_module':{'resources':[{'type':'azurerm_application_gateway','values':gateway},{'type':'azurerm_web_application_firewall_policy','values':{'policy_settings':[{'enabled':True,'mode':'Prevention'}]}}]}}}

    def test_public_plan_rejects_detection_mode_and_disabled_tls_validation(self):
        plan=self.plan();check_public_plan(plan)
        plan['planned_values']['root_module']['resources'][1]['values']['policy_settings'][0]['mode']='Detection'
        with self.assertRaises(ConfigError):check_public_plan(plan)
        plan=self.plan();plan['planned_values']['root_module']['resources'][0]['values']['backend_http_settings'][0]['sni_validation_enabled']=False
        with self.assertRaises(ConfigError):check_public_plan(plan)

    def test_public_plan_rejects_embedded_private_certificate_and_deletions(self):
        plan=self.plan();plan['planned_values']['root_module']['resources'][0]['values']['ssl_certificate'][0]['data']='pfx-value'
        with self.assertRaises(ConfigError):check_public_plan(plan)
        plan=self.plan();plan['resource_changes']=[{'mode':'managed','change':{'actions':['delete','create']}}]
        with self.assertRaises(ConfigError):check_public_plan(plan)


class PortalArtifactTests(unittest.TestCase):
    def test_public_portals_preserve_the_swa_default_document_and_origin_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'apps/portal/out';out.mkdir(parents=True)
            cfg={'environment':'dev','deploy_demo':True,'web_portals':{'tenant':{'view':'tenant'},'operations':{'view':'admin'}},'enable_api_tenant':True}
            platform={'vault':{'name':'private-vault'},'public_origin':'https://gateway.unit.test','public_entrypoint_ip':'8.8.8.8','webs':{'tenant':{},'operations':{}},'auth':{}}
            view=SimpleNamespace(cfg=cfg,path=root,output=lambda stage:platform if stage=='platform' else {})
            deployed=[]
            def execute(args,**kwargs):
                if args[0]=='npm' and 'build' in args:
                    prefix=kwargs['env_updates']['NEXT_PUBLIC_BASE_PATH']
                    (out/'index.html').write_text('<script>console.log("boot")</script>'+prefix)
                    (out/'staticwebapp.config.json').write_text('{}')
                if args[0]=='swa':
                    artifact=Path(args[2]);config=json.loads((artifact/'staticwebapp.config.json').read_text())
                    self.assertTrue((artifact/'index.html').is_file(),'SWA requires a default document at its artifact root')
                    self.assertEqual(config['networking']['allowedIpRanges'],['8.8.8.8/32'])
                    self.assertEqual(args[args.index('--swa-config-location')+1],str(artifact))
                    self.assertNotIn('fixture-deployment-token',args)
                    nested=next(artifact.glob('dev/*/config.json'));metadata=json.loads(nested.read_text())
                    self.assertEqual(metadata['gateway'],'https://gateway.unit.test/dev')
                    self.assertFalse((nested.parent/'staticwebapp.config.json').exists())
                    self.assertEqual((artifact/'index.html').read_text(),(nested.parent/'index.html').read_text())
                    deployed.append(metadata['role'])
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            with patch.object(operations,'ROOT',root),patch.object(operations,'secret_value',return_value='fixture-deployment-token'):
                operations.publish_web_portals(view,execute)
            self.assertEqual(deployed,['tenant','admin'])
