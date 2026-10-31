"""Install a fixed official binary, checked against a versioned SHA-256 manifest."""
import hashlib
import io
import json
import platform
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(name):
    tools = json.loads((ROOT / 'scripts/security-tools.json').read_text())
    spec = tools[name]
    system = {'Darwin': 'darwin', 'Linux': 'linux'}.get(platform.system())
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'AMD64': 'x64'}.get(platform.machine())
    asset = spec['assets'].get(f'{system}-{arch}')
    if not asset:
        raise SystemExit(f'Unsupported platform for {name}.')
    url = f"https://github.com/{spec['repository']}/releases/download/v{spec['version']}/{asset['name']}"
    data = urllib.request.urlopen(url, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != asset['sha256']:
        raise SystemExit(f'{name} checksum mismatch; executable was not installed.')
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        member = archive.getmember(name)
        if not member.isfile():
            raise SystemExit('Tool archive does not contain the expected regular executable.')
        content = archive.extractfile(member).read()
    destination = ROOT / '.lz/security-tools' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    destination.chmod(0o755)
    print(f"Official {name} {spec['version']} installed; pinned SHA-256 verified.")
