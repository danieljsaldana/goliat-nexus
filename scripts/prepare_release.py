#!/usr/bin/env python3
"""Prepare audited release files and checksums locally; never publishes anything."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from publication import ROOT, public_files, validate_artifacts


def prepare(output, version):
    expected = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', version) or version != expected:
        raise ValueError('Release version must match VERSION exactly.')
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new release output directory; existing files are preserved.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    if dirty:
        raise ValueError('Release requires a clean source checkout.')
    files = public_files()
    checksums = [f'{hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}  {path.as_posix()}' for path in files]
    output.mkdir(parents=True, mode=0o700)
    (output / 'SOURCE_SHA256SUMS').write_text('\n'.join(checksums) + '\n')
    provenance = {'product': 'Goliat Nexus', 'version': version, 'source_commit': commit,
                  'working_tree_dirty': dirty, 'workflow_run': os.environ.get('GITHUB_RUN_ID'),
                  'source_files': len(files), 'distribution': 'Git source; no product archives'}
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    (output / 'release-notes.md').write_text(
        f'Goliat Nexus {version}\n\nShared Azure hub, isolated Dev/Prod environments and the Alba example application. '
        'The tenant and admin portals are example interfaces to adapt to your project.\n\n'
        'All infrastructure, application and configuration source is versioned in this repository. '
        'No custom ZIP assets are generated.\n\n'
        'Review the CI and security results, production checklist and SOURCE_SHA256SUMS before publishing this draft.\n'
    )
    validate_artifacts(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output, args.version)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f'Release files prepared at {result}; nothing was published.')


if __name__ == '__main__':
    main()
