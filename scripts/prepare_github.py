#!/usr/bin/env python3
"""Prepare a fresh local Git checkout with public source only. Never pushes."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from publication import ROOT, public_files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='.local/github-ready/goliat-nexus')
    args=parser.parse_args()
    destination=(ROOT/args.output).resolve()
    if destination.exists():raise SystemExit('Output already exists; choose a new empty destination.')
    subprocess.run(['python3',str(ROOT/'scripts/check_publication.py'),'--history'],check=True,cwd=ROOT)
    files=public_files()
    destination.mkdir(parents=True,mode=0o700)
    for file in files:
        target=destination/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/file,target)
    ignore=destination/'.gitignore'
    ignore.write_text(ignore.read_text()+'\n# Local hosting integration metadata\n.openai/\n')
    project=json.loads((ROOT/'site/content/project.json').read_text())
    for command in (['git','init','--initial-branch=main'],['git','remote','add','origin',project['repository']+'.git'],['git','config','core.hooksPath','.githooks']):
        subprocess.run(command,cwd=destination,check=True,capture_output=True)
    print(f'Prepared {len(files)} source files at {destination}. Fresh Git history, no commits and no push.')


if __name__=='__main__':
    main()
