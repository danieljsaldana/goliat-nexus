#!/usr/bin/env python3
"""Refresh public-facing star metadata with the operator's GitHub CLI session."""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
project = json.loads((ROOT / 'site/content/project.json').read_text())
repository = project['repository']
if not re.fullmatch(r'https://github\.com/[\w-]+/[\w.-]+', repository):
    raise SystemExit('Invalid project repository URL.')
result = subprocess.run(['gh', 'repo', 'view', repository, '--json', 'url,stargazerCount'], capture_output=True, text=True)
if result.returncode:
    raise SystemExit('GitHub metadata unavailable. Check gh authentication; existing metadata was preserved.')
data = json.loads(result.stdout)
count = data.get('stargazerCount')
if data.get('url') != repository or type(count) is not int or count < 0:
    raise SystemExit('Unexpected GitHub repository metadata; existing snapshot was preserved.')
snapshot = {'repository': repository, 'count': count, 'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
(ROOT / 'site/content/github-stars.json').write_text(json.dumps(snapshot, indent=2) + '\n')
print(f'GitHub stars verified: {count}. No credentials are stored in the snapshot.')
