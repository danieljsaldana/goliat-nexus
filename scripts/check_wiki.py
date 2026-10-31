#!/usr/bin/env python3
"""Check the local wiki source without contacting or updating GitHub."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'docs/wiki'
slugs = {page.stem for page in folder.glob('*.md')}
repository = json.loads((ROOT / 'site/content/project.json').read_text())['repository']
for page in folder.glob('*.md'):
    text = page.read_text()
    if text.count('```') % 2:
        raise SystemExit(f'Unclosed code fence: {page.name}')
    for slug in re.findall(re.escape(repository) + r'/wiki/([A-Za-z0-9_-]+)', text):
        if slug not in slugs:
            raise SystemExit(f'Broken wiki link in {page.name}: {slug}')
print(f'Wiki source verified: {len(slugs)} pages/navigation files; no remote changes.')
