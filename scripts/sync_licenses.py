#!/usr/bin/env python3
"""Keep legal notices in independently built application contexts."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ('apps/api', 'apps/functions', 'apps/frontend', 'apps/certificates', 'apps/portal/public')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for context in CONTEXTS:
        for name in ('LICENSE', 'NOTICE'):
            source = (ROOT / name).read_bytes()
            target = ROOT / context / name
            if target.is_file() and target.read_bytes() == source:
                continue
            if args.check:
                stale.append(f'{context}/{name}')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source)
    if stale:
        raise SystemExit('Stale application licence notices: run python3 scripts/sync_licenses.py')
    print('Application licence notices verified.' if args.check else 'Application licence notices synchronised.')


if __name__ == '__main__':
    main()
