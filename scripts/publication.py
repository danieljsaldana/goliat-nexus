"""Allowlisted source files for a clean GitHub checkout, without archives."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TFVARS = {'examples/shared.auto.tfvars.json', *[f'{folder}/{name}.tfvars' for folder in ('environments','examples/demo') for name in ('common','dev','prod')]}
PUBLIC_TEMPLATES = {'examples/agent/local.auto.tfvars.example'}
PUBLIC_ROOTS = {'.github','.githooks','.gitignore','Makefile','README.md','README.es.md','SECURITY.md','LICENSE','NOTICE','CONTRIBUTING.md','VERSION','lz',
    'modules','product','stacks','terraform','environments','examples','tests','scripts','docs','site','apps','package.json','package-lock.json'}
PRIVATE_PARTS = {'.git','.local','.lz','.openai','.sites-runtime','.terraform','node_modules','__pycache__','.next','out','dist','.generated','.azure','.aws','.ssh','coverage','test-results','playwright-report','.venv','venv','.pytest_cache','.mypy_cache','.terraform.d'}
GENERATED_SITE = {'docs','examples','environments','downloads','licenses','.generated'}
PRIVATE_SUFFIXES = {'.pem','.key','.pfx','.p12','.jks','.keystore','.kdbx','.tfstate','.tfplan','.pyc','.sqlite','.sqlite3','.db'}
ARCHIVE_SUFFIXES = {'.zip', '.tar', '.gz', '.tgz', '.7z', '.rar'}


def private_reason(path):
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in ARCHIVE_SUFFIXES:
        return 'archives are not published; use the source repository'
    if PRIVATE_PARTS.intersection(part.lower() for part in path.parts):
        return 'local, generated or credential directory'
    if name in ('.npmrc','.pypirc','.netrc','.git-credentials','id_rsa','id_ed25519','id_ecdsa','credentials.json','azureprofile.json','msal_token_cache.json','accesstokens.json'):
        return 'local authentication material'
    if suffix in ('.log','.har'):
        return 'runtime log or browser capture'
    if name.startswith('.env') and name not in ('.env.example','.env.sample'):
        return 'environment credentials'
    if suffix in PRIVATE_SUFFIXES or '.tfstate.' in name or '.tfplan.' in name:
        return 'credential or Terraform runtime artifact'
    if (name.endswith('.tfvars') or '.tfvars.' in name) and path.as_posix() not in PUBLIC_TFVARS | PUBLIC_TEMPLATES:
        return 'unapproved Terraform variables'
    if name in ('override.tf','override.tf.json') or name.endswith(('_override.tf','_override.tf.json')):
        return 'local Terraform override'
    return None


def candidate_files():
    result = subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,check=True,capture_output=True)
    return sorted({Path(name) for name in result.stdout.decode().split('\0') if name and (ROOT/name).is_file()})


def public_files():
    files = []
    for path in candidate_files():
        if path.parts[0] not in PUBLIC_ROOTS or private_reason(path):
            continue
        if path.parts[0] == 'docs' and path.suffix.lower() == '.html':
            continue
        if path.parts[0]=='site':
            if len(path.parts)>1 and path.parts[1] in GENERATED_SITE:
                continue
            if path.as_posix()=='site/SOURCES.json' or (path.parts[1]=='diagrams' and path.suffix=='.html'):
                continue
        if (ROOT/path).is_symlink():
            raise ValueError('Symlinks are not accepted in the publication source: '+path.as_posix())
        files.append(path)
    return files


def validate_example_identifiers():
    """Real Azure identifiers must never replace the published example values."""
    import json
    import sys
    sys.path.insert(0, str(ROOT))
    from product.tfvars import read_environment_directory
    zero = '00000000-0000-0000-0000-000000000000'
    configurations = [read_environment_directory(ROOT / folder) for folder in ('environments', 'examples/demo')]
    configurations.append(json.loads((ROOT / 'examples/shared.json').read_text()))
    native = json.loads((ROOT / 'examples/shared.auto.tfvars.json').read_text())
    configurations.append(native['config'])
    for cfg in configurations:
        for key in ('subscription_id', 'tenant_id', 'operator_object_id'):
            if cfg.get(key) != zero:
                raise ValueError(f'Published examples contain a non-fictional {key}; value withheld.')


def validate_artifacts(directory):
    """Reject private paths, symlinks and archives before scanning static output."""
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError('Artifact directory does not exist.')
    files = list(directory.rglob('*'))
    count = 0
    for file in files:
        if file.is_symlink():
            raise ValueError('Artifact symlinks are not allowed.')
        if not file.is_file():
            continue
        path = file.relative_to(directory)
        if '\\' in path.as_posix() or ':' in path.parts[0]:
            raise ValueError('Unsafe artifact path; contents withheld.')
        if path.parts[0] == 'site':
            path = Path(*path.parts[1:])
        reason = private_reason(path)
        if reason:
            raise ValueError(f'Private artifact path ({reason}); contents withheld.')
        count += 1
    return count
