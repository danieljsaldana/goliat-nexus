import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import prepare_release
import security_tools


class ReleasePreparationTests(unittest.TestCase):
    def test_bad_version_and_existing_destination_cannot_replace_release_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'VERSION').write_text('1.0.0')
            with patch.object(prepare_release, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'match VERSION'):
                    prepare_release.prepare(root / 'release', '1.0.0; command')
            self.assertFalse((root / 'release').exists())

    def test_checksums_match_versioned_source_without_generating_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'VERSION').write_text('1.0.0')
            files = [Path('README.md'), Path('VERSION')]
            (root / 'README.md').write_text('Fictional release fixture')
            with patch.object(prepare_release, 'ROOT', root), patch.object(prepare_release, 'public_files', return_value=files), patch.object(prepare_release.subprocess, 'check_output', side_effect=['a' * 40, '']):
                output = prepare_release.prepare(root / 'release', '1.0.0')
            for line in (output / 'SOURCE_SHA256SUMS').read_text().splitlines():
                digest, name = line.split()
                self.assertEqual(digest, hashlib.sha256((root / name).read_bytes()).hexdigest())
            self.assertEqual(json.loads((output / 'provenance.json').read_text())['source_commit'], 'a' * 40)
            self.assertFalse(list(output.glob('*.zip')))
            self.assertEqual({p.name for p in output.iterdir()}, {'SOURCE_SHA256SUMS', 'provenance.json', 'release-notes.md'})
            with patch.object(prepare_release, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'existing files are preserved'):
                    prepare_release.prepare(output, '1.0.0')

    def test_dirty_source_cannot_be_presented_as_a_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'VERSION').write_text('1.0.0')
            with patch.object(prepare_release, 'ROOT', root), patch.object(prepare_release.subprocess, 'check_output', side_effect=['a' * 40, ' M README.md']):
                with self.assertRaisesRegex(ValueError, 'clean source checkout'):
                    prepare_release.prepare(root / 'release', '1.0.0')
            self.assertFalse((root / 'release').exists())


class ToolIntegrityTests(unittest.TestCase):
    def test_a_modified_tool_archive_is_rejected_before_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            manifest = {'tool': {'version': '1.0.0', 'repository': 'official/tool', 'assets': {
                'linux-x64': {'name': 'tool.tar.gz', 'sha256': hashlib.sha256(b'expected').hexdigest()}}}}
            (root / 'scripts/security-tools.json').write_text(json.dumps(manifest))
            with patch.object(security_tools, 'ROOT', root), patch.object(security_tools.platform, 'system', return_value='Linux'), patch.object(security_tools.platform, 'machine', return_value='x86_64'), patch.object(security_tools.urllib.request, 'urlopen', return_value=io.BytesIO(b'modified')):
                with self.assertRaisesRegex(SystemExit, 'checksum mismatch'):
                    security_tools.install('tool')
            self.assertFalse((root / '.lz/security-tools/tool').exists())
