import io
import json
import tempfile
import unittest
import zipfile
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import Mock, patch

from product.cli import Deployment, fixture_contracts
from product.config import ConfigError, normalize
from product.operations import application_get, application_token, isolated_docker_config, publish_application_code, publish_example, publish_web_portals, published_images, smoke_test, wait_for_applications
from test_product import raw_config


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.deployment = Deployment(normalize(raw_config()))
        self.deployment.path = Path(self.temporary.name)
        _, platform = fixture_contracts(self.deployment.cfg)
        self.platform = platform["environments"]["dev"]
        self.deployment.output = Mock(return_value=platform)
        self.view = self.deployment.environment_view("dev")

    def build(self, args, **kwargs):
        if '--metadata-file' in args:
            component = Path(args[-1]).name
            digest = ('a' if component == 'api' else 'b') * 64
            Path(args[args.index('--metadata-file') + 1]).write_text(json.dumps({'containerimage.digest': f'sha256:{digest}'}))
        return Mock(returncode=0, stdout='')

    @patch('product.operations.secret_value', return_value='test-deployment-token')
    def test_custom_portal_uses_its_own_secret_and_the_selected_reference_view(self, secret):
        self.view.cfg['web_portals'] = {'support': {'view': 'tenant'}}
        platform = {**self.platform, 'webs': {'support': {'name': 'support-site', 'hostname': 'support.azurestaticapps.net', 'view': 'tenant'}}}
        self.view.output = lambda stage: platform if stage == 'platform' else {'demo_url': 'https://gateway.test'}
        root = Path(self.temporary.name) / 'source'
        (root / 'apps/portal/out').mkdir(parents=True)
        (root / 'apps/portal/out/index.html').write_text('Alba')
        published = []
        def execute(args, **kwargs):
            if args[0] == 'swa':
                config = json.loads((Path(args[2]) / 'config.json').read_text())
                published.append(config)
                self.assertEqual(kwargs['env_updates']['SWA_CLI_DEPLOYMENT_TOKEN'], 'test-deployment-token')
                self.assertNotIn('test-deployment-token', args)
            return Mock(returncode=0, stdout='')
        with patch('product.operations.ROOT', root):
            publish_web_portals(self.view, execute)
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]['role'], 'tenant')
        self.assertTrue(published[0]['features']['enable_event_processing'])
        secret.assert_called_once_with(execute, self.platform['vault']['name'], 'deploy-web-support')

    @patch('product.operations.time.sleep')
    @patch('product.operations.urlopen')
    def test_read_retries_a_cold_start_but_never_retries_denied_authentication(self, open_url, sleep):
        body = io.BytesIO(b'{"items":[]}');body.status = 200
        open_url.side_effect = [HTTPError('https://api.test', 503, 'Starting', {}, None), body]
        self.assertEqual(application_get('https://api.test', 'token'), {'items': []})
        sleep.assert_called_once_with(5)
        sleep.reset_mock();open_url.reset_mock()
        open_url.side_effect = HTTPError('https://api.test', 401, 'Denied', {}, None)
        with self.assertRaises(HTTPError):
            application_get('https://api.test', 'invalid-token')
        self.assertEqual(open_url.call_count, 1)
        sleep.assert_not_called()

    @patch('product.operations.time.sleep')
    def test_waits_for_new_revision_instead_of_accepting_the_previous_ready_revision(self, sleep):
        self.view.output = Mock(return_value={'applications': {'tenant': {'id': '/test/app'}}})
        execute = Mock(side_effect=[Mock(stdout='{"latest":"new","ready":"old"}'), Mock(stdout='{"latest":"new","ready":"new"}')])
        wait_for_applications(self.view, execute)
        self.assertEqual(execute.call_count, 2)
        sleep.assert_called_once_with(5)

    @patch('product.operations.time.monotonic', side_effect=[0, 601])
    def test_wait_for_revision_times_out_without_reporting_success(self, monotonic):
        self.view.output = Mock(return_value={'applications': {'tenant': {'id': '/test/app'}}})
        execute = Mock(return_value=Mock(stdout='{"latest":"new","ready":"old"}'))
        with self.assertRaisesRegex(ConfigError, 'no están listas: tenant'):
            wait_for_applications(self.view, execute)

    @patch('product.operations.sys.platform', 'linux')
    @patch('product.operations.private_address')
    def test_functions_package_contains_locked_dependencies_without_remote_build(self, private_address):
        self.view.cfg['enable_event_processing'] = True
        self.view.output = lambda stage: {**self.platform, 'webs': {}} if stage == 'platform' else {
            'functions': {'name': 'events', 'hostname': 'events.azurewebsites.net', 'resource_group': 'dev-rg'}}
        packages = []
        def execute(args, **kwargs):
            if args[0] == 'npm':
                self.assertEqual(args[-2:], ['ci', '--omit=dev'])
                dependency = Path(args[2]) / 'node_modules/@azure/functions/index.js'
                dependency.parent.mkdir(parents=True)
                dependency.write_text('export {};')
                dependency.chmod(0o600)
                dependency.parent.chmod(0o700)
            else:
                self.assertEqual(args[args.index('--build-remote') + 1], 'false')
                with zipfile.ZipFile(args[args.index('--src') + 1]) as archive:
                    packages.append(set(archive.namelist()))
                    self.assertEqual(archive.getinfo('node_modules/@azure/functions/index.js').external_attr >> 16 & 0o777, 0o644)
                    self.assertEqual(archive.getinfo('node_modules/@azure/functions/').external_attr >> 16 & 0o777, 0o755)
            return Mock(returncode=0, stdout='')
        publish_application_code(self.view, execute)
        self.assertEqual(len(packages), 1)
        self.assertTrue({'host.json', 'domain.mjs', 'package-lock.json', 'node_modules/@azure/functions/index.js'} <= packages[0])
        private_address.assert_called_once()

    @patch('product.cli.execute')
    def test_acquires_delegated_application_token_without_printing_credentials(self, execute):
        execute.return_value = Mock(stdout='test-delegated-token\n')
        self.assertEqual(application_token(self.view), 'test-delegated-token')
        arguments = execute.call_args.args[0]
        self.assertEqual(arguments[arguments.index('--scope') + 1], self.platform['auth']['scope'])
        self.assertTrue(execute.call_args.kwargs['capture'])
        self.assertTrue(execute.call_args.kwargs['redact_errors'])

    @patch('product.operations.shutil.which', return_value='/mock/docker')
    @patch('product.operations.private_address')
    def test_publishes_both_images_and_passes_digests_to_terraform(self, _address, _which):
        execute = Mock(side_effect=self.build)
        images = publish_example(self.view, execute)
        self.assertEqual(images, published_images(self.view, self.platform))
        self.deployment.inputs('dev', self.platform)
        inputs = json.loads((self.deployment.path / 'stacks/dev/inputs.auto.tfvars.json').read_text())
        self.assertEqual(inputs['sample_images'], images)
        self.assertIn('@sha256:', images['frontend'])
        build = [c.args[0] for c in execute.call_args_list if '--push' in c.args[0]]
        self.assertEqual(len(build), 2)
        self.assertNotIn(':'+self.view.cfg['sample']['version'], images['api'])

    def test_registry_login_is_isolated_without_losing_docker_context_or_plugins(self):
        source = self.deployment.path / 'original-docker'
        destination = self.deployment.path / 'temporary-docker'
        source.mkdir()
        destination.mkdir()
        for name in ('contexts', 'cli-plugins'):
            (source / name).mkdir()
        original = {'currentContext': 'desktop-linux', 'auths': {'example.test': {'auth': 'test-only'}}, 'credsStore': 'desktop'}
        (source / 'config.json').write_text(json.dumps(original))
        with patch.dict('os.environ', {'DOCKER_CONFIG': str(source), 'BUILDX_CONFIG': str(source/'buildx')}):
            env = isolated_docker_config(destination)
        self.assertEqual(json.loads((destination/'config.json').read_text()), {'currentContext': 'desktop-linux'})
        self.assertEqual((destination/'contexts').resolve(), (source/'contexts').resolve())
        self.assertEqual((destination/'cli-plugins').resolve(), (source/'cli-plugins').resolve())
        self.assertEqual(env['BUILDX_CONFIG'], str(source/'buildx'))
        self.assertEqual(json.loads((source/'config.json').read_text()), original)

    @patch('product.operations.shutil.which', return_value='/mock/docker')
    @patch('product.operations.private_address')
    def test_partial_build_preserves_last_complete_publication(self, _address, _which):
        path = self.view.path / 'images.json'
        path.write_text('previous-complete-release')
        def failing(args, **kwargs):
            if args[-1].endswith('/frontend'):
                raise ConfigError('Build failed')
            return self.build(args, **kwargs)
        with self.assertRaises(ConfigError):
            publish_example(self.view, failing)
        self.assertEqual(path.read_text(), 'previous-complete-release')

    @patch('product.operations.shutil.which', return_value='/mock/docker')
    @patch('product.operations.private_address')
    def test_invalid_digest_never_promotes_publication(self, _address, _which):
        def invalid(args, **kwargs):
            if '--metadata-file' in args:
                Path(args[args.index('--metadata-file') + 1]).write_text('{"containerimage.digest":"latest"}')
        with self.assertRaisesRegex(ConfigError, 'Digest'):
            publish_example(self.view, invalid)
        self.assertFalse((self.view.path / 'images.json').exists())

    def test_missing_manifest_blocks_workload_plan(self):
        with self.assertRaisesRegex(ConfigError, 'publish-example'):
            self.deployment.inputs('dev', self.platform)

    @patch('product.operations.shutil.which', return_value='/mock/docker')
    @patch('product.operations.private_address')
    def test_different_registry_or_version_cannot_reuse_manifest(self, _address, _which):
        publish_example(self.view, self.build)
        with self.assertRaises(ConfigError):
            published_images(self.view, {**self.platform, 'registry_login_server': 'other.azurecr.io'})
        self.deployment.cfg['environments']['dev']['sample']['version'] = 'next-release'
        with self.assertRaises(ConfigError):
            published_images(self.view, self.platform)

    @patch('product.operations.shutil.which', return_value=None)
    def test_missing_tools_fail_before_registering_or_creating_resources(self, _which):
        self.deployment.register_providers = Mock()
        self.deployment.tf = Mock()
        with self.assertRaisesRegex(ConfigError, 'docker'):
            self.deployment.deploy('all')
        self.deployment.register_providers.assert_not_called()
        self.deployment.tf.assert_not_called()

    @patch('product.operations.application_token', return_value='test-token')
    @patch('product.operations.private_address')
    @patch('product.operations.urlopen')
    def test_smoke_test_requires_the_actual_api_contract(self, open_url, _address, _token):
        self.view.output = lambda stage: self.platform if stage == 'platform' else {'demo_url': 'https://frontend.test'}
        for response in [b'{}', b'[]', b'<html>fallback</html>', b'{"status":"ok","database":"disabled"}']:
            body = io.BytesIO(response)
            body.status = 200
            open_url.return_value = body
            with self.subTest(response=response), self.assertRaises(ConfigError):
                smoke_test(self.view)
        body = io.BytesIO(b'{"items":[]}')
        body.status = 200
        open_url.return_value = body
        smoke_test(self.view)
