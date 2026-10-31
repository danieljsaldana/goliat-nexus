#!/usr/bin/env python3
"""Audit publication source, Git history and optional artifacts without leaking values."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from publication import ROOT, candidate_files, private_reason, public_files, validate_artifacts, validate_example_identifiers


def scan(binary, mode, directory, report, *, history=False):
    command = [str(binary), mode, str(directory), '--redact=100', '--no-banner',
               '--report-format', 'json', '--report-path', str(report), '--max-archive-depth', '2']
    if history:
        command += ['--log-opts=--all']
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        findings = json.loads(report.read_text()) if report.exists() else []
        for finding in findings:
            print(f"Blocked by {finding['RuleID']} at line {finding['StartLine']}; path and value withheld.")
        raise SystemExit('Secret scan failed. Nothing was uploaded. Inspect Gitleaks locally with redaction.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Scan all local Git refs.')
    parser.add_argument('--strict-tracked', action='store_true', help='Reject every tracked file outside the publication allowlist (CI/clean checkout).')
    parser.add_argument('--artifacts', type=Path, help='Inspect and scan generated output; archives are forbidden.')
    args = parser.parse_args()
    files = public_files()
    tracked = [Path(p) for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0') if p]
    blocked = [p for p in tracked if private_reason(p) and (args.strict_tracked or p.parts[0] != '.openai')]
    if args.strict_tracked:
        blocked += [p for p in tracked if p not in files]
    if blocked:
        raise SystemExit('Tracked files cross the publication boundary; file names withheld. Inspect git ls-files locally.')
    validate_example_identifiers()
    binary = shutil.which('gitleaks') or str(ROOT / '.lz/security-tools/gitleaks')
    if not Path(binary).is_file():
        raise SystemExit('Install the pinned scanner: python3 scripts/install_gitleaks.py')
    with tempfile.TemporaryDirectory(prefix='goliat-publication-') as temp:
        folder = Path(temp)
        source = folder / 'source'
        source.mkdir()
        # Scan all non-ignored working source, including files outside the export
        # allowlist. Local credential/config directories remain excluded.
        for file in candidate_files():
            if private_reason(file) and file.parts[0] != '.openai':
                continue
            if (ROOT / file).is_symlink():
                raise SystemExit('Source symlink rejected; no files were uploaded.')
            target = source / file
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / file, target)
        scan(binary, 'dir', source, folder / 'source.json')
        has_history = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT, capture_output=True).returncode == 0
        if args.history and has_history:
            scan(binary, 'git', ROOT, folder / 'history.json', history=True)
        if args.artifacts:
            count = validate_artifacts(args.artifacts)
            scan(binary, 'dir', args.artifacts.resolve(), folder / 'artifacts.json')
            print(f'Artifact boundaries and contents verified: {count} files; no archives.')
    print(f'Publication check passed: {len(files)} public source files; no detected credentials; real configuration excluded.' + (' All local Git refs also checked.' if args.history and has_history else ''))


if __name__ == '__main__':
    main()
