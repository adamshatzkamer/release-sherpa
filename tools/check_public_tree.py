"""Inspect Git-indexed files (or source files before git init) for private artifacts."""
import ipaddress
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def issues(name, text):
    found = []
    parts = Path(name).parts
    if (any(p in ('state', '__pycache__', '.venv', 'node_modules') for p in parts)
        or Path(name).name in ('config.json', 'bridge.local.json', 'bridge-config.json')
        or (Path(name).name.startswith('.env') and Path(name).name != '.env.example')
        or Path(name).suffix in ('.pyc', '.log', '.pem', '.key', '.vsix')):
        found.append('private/generated artifact')
    for pattern in (r'/[U]sers/[^/\s]+/', r'/[h]ome/[^/\s]+/',
                    r'\b[UBCT]0[A-Z0-9]{8,}\b',
                    r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'):
        if re.search(pattern, text):
            found.append('possible personal path or service/account identifier')
            break
    for value in re.findall(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', text):
        try:
            address = ipaddress.ip_address(value)
            if not address.is_loopback and value != '0.0.0.0':
                found.append('non-loopback IP address')
                break
        except ValueError:
            pass
    return found


def main():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        names = [n.decode() for n in result.stdout.split(b'\0') if n]
        if not names:
            raise SystemExit('No indexed files. Stage the intended public files before auditing.')
    else:
        names = [str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()
                 and not any(part in ('.git', '__pycache__') for part in p.relative_to(ROOT).parts)]
    failures = []
    for name in names:
        if result.returncode == 0:
            # Check the staged bytes, not a possibly different working-tree version.
            data = subprocess.run(['git', 'show', ':' + name], cwd=ROOT, check=True, capture_output=True).stdout
        else:
            data = (ROOT / name).read_bytes()
        for reason in issues(name, data.decode('utf-8', errors='replace')):
            failures.append(name + ': ' + reason)
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'Public-tree check passed: {len(names)} files. Also run a secret scanner and review proprietary content.')


if __name__ == '__main__':
    main()
