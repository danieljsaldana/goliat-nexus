import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import publication
from site_metadata import render_head


class PublicationTests(unittest.TestCase):
    def test_operational_files_are_rejected_even_when_forced_into_git(self):
        for name in ('apps/api/.env.production','keys/identity.pfx','keys/private.key','environments/local.auto.tfvars.json','environments/dev.tfvars.bak','terraform.tfstate.backup','deployment.tfplan.json','apps/trace.har','id_ed25519','.npmrc'):
            with self.subTest(name=name):self.assertIsNotNone(publication.private_reason(Path(name)))
        for name in publication.PUBLIC_TFVARS | publication.PUBLIC_TEMPLATES:
            with self.subTest(name=name):self.assertIsNone(publication.private_reason(Path(name)))

    def test_export_omits_hosting_identity_private_files_and_generated_downloads(self):
        names=[Path(name) for name in ('README.md','site/index.html','.openai/hosting.json','.local/user.json','site/downloads/old.zip','keys/identity.pfx','modules/network/main.tf')]
        with patch.object(publication,'candidate_files',return_value=names):
            self.assertEqual(publication.public_files(),[Path('README.md'),Path('site/index.html'),Path('modules/network/main.tf')])

    def test_export_cannot_follow_a_symlink_to_a_private_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'private').write_text('not for publication');(root/'README.md').symlink_to(root/'private')
            with patch.object(publication,'ROOT',root),patch.object(publication,'candidate_files',return_value=[Path('README.md')]):
                with self.assertRaisesRegex(ValueError,'Symlinks'):publication.public_files()

    def test_sharing_urls_keep_the_project_subpath_and_code_repository(self):
        profile={'name':'Nexus','description':'Sample','author':{'name':'Author','url':'https://example.com/'},'social_image':'assets/social-card.png','social_image_alt':'Hub','locale':'es_ES','version':'1.0.0','repository':'https://github.com/example/nexus','website':'https://example.github.io/nexus/'}
        head=render_head(profile,site_url='https://example.com/project/')
        self.assertIn('https://example.com/project/assets/social-card.png',head)
        self.assertIn('"codeRepository": "https://github.com/example/nexus"',head)
        self.assertIn('name="author" content="Author"',head)
        with self.assertRaises(ValueError):render_head(profile,site_url='https://user:credential@example.com/')


class ArtifactBoundaryTests(unittest.TestCase):
    def test_private_files_and_archives_are_rejected_in_static_output(self):
        for name in ['.env', '.lz/identity.json', 'private.tfvars', 'key.pem', '.ENV', 'identity.PFX', 'package.zip', 'package.ZIP', 'package.tar.gz', 'docs/archive.7z']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fictional fixture')
                with self.assertRaises(ValueError):
                    publication.validate_artifacts(folder)
                self.assertIsNotNone(publication.private_reason(Path(name)))

    def test_plain_documented_configuration_is_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'environments/dev.tfvars'
            path.parent.mkdir()
            path.write_text('fictional fixture')
            self.assertEqual(publication.validate_artifacts(folder), 1)

    def test_artifact_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'public.txt'
            target.write_text('public')
            (Path(folder) / 'alias.txt').symlink_to(target)
            with self.assertRaises(ValueError):
                publication.validate_artifacts(folder)

    def test_real_azure_identifiers_cannot_replace_public_example_placeholders(self):
        cfg={'subscription_id':'00000000-0000-0000-0000-000000000000','tenant_id':'12345678-1234-1234-1234-123456789012','operator_object_id':'00000000-0000-0000-0000-000000000000'}
        with patch('product.tfvars.read_environment_directory',return_value=cfg):
            with self.assertRaisesRegex(ValueError,'non-fictional tenant_id'):
                publication.validate_example_identifiers()
