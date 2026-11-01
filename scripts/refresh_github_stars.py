#!/usr/bin/env python3
"""Refresh the public, dated fallback used when daily metadata is unavailable."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from publish_github_stars import GitHub, snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    repository = json.loads((ROOT / 'site/content/project.json').read_text())['repository']
    if not re.fullmatch(r'https://github\.com/[\w-]+/[\w.-]+', repository):
        raise SystemExit('Invalid project repository URL.')
    data = snapshot(repository.removeprefix('https://github.com/'), GitHub(), datetime.now(timezone.utc))
    (ROOT / 'site/content/github-stars.json').write_text(json.dumps(data, indent=2) + '\n')
    print(f"GitHub stars verified: {data['count']}. Only public metadata was stored.")


if __name__ == '__main__':
    main()
