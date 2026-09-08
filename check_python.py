"""Run the configured repository test suite with no network and no inherited secrets."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    python = os.environ.get('SHEPHERD_TEST_PYTHON', '')
    if not python or not Path(python).is_file():
        raise SystemExit('Set SHEPHERD_TEST_PYTHON to an existing Python environment with the project test dependencies')
    with tempfile.TemporaryDirectory(prefix='shepherd-test-') as home:
        env = {'PATH': str(Path(python).parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
               'HOME': home, 'TMPDIR': home, 'LANG': 'en_US.UTF-8',
               'DATABASE_URL': 'sqlite:///:memory:', 'FLASK_ENV': 'testing',
               'AWS_EC2_METADATA_DISABLED': 'true', 'AWS_ACCESS_KEY_ID': 'testing',
               'AWS_SECRET_ACCESS_KEY': 'testing', 'AWS_DEFAULT_REGION': 'us-east-1',
               'PYTHONDONTWRITEBYTECODE': '1'}
        result = subprocess.run(['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)',
                                 python, '-m', 'pytest', '-q'], env=env)
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
