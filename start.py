"""Bootstrap the environment and run the service (Python 3.10+)."""
import argparse
import hashlib
import os
from pathlib import Path
import ssl
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8011)
    parser.add_argument('--cert', default=os.environ.get('SSL_CERTFILE'))
    parser.add_argument('--key', default=os.environ.get('SSL_KEYFILE'))
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('Python 3.10 or newer is required')
    cert, key = args.cert, args.key
    if not cert and not key and (ROOT / 'certs/fullchain.pem').exists():
        cert, key = 'certs/fullchain.pem', 'certs/privkey.pem'
    if bool(cert) != bool(key):
        parser.error('Provide both --cert and --key')
    if cert:
        cert, key = str((ROOT / cert).resolve()), str((ROOT / key).resolve())
        try:
            ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cert, key)
        except (OSError, ssl.SSLError) as exc:
            parser.error(f'Invalid TLS certificate/key: {exc}')
    env = ROOT / '.venv'
    python = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    requirements = ROOT / 'requirements.txt'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = env / '.requirements.sha256'
    if not stamp.exists() or stamp.read_text().strip() != digest:
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        stamp.write_text(digest)
    command = [str(python), '-m', 'uvicorn', 'app:app', '--host', args.host,
               '--port', str(args.port), '--workers', '1']
    if cert:
        command += ['--ssl-certfile', cert, '--ssl-keyfile', key]
    scheme = 'https' if cert else 'http'
    print(f'Swagger: {scheme}://localhost:{args.port}/docs', flush=True)
    os.chdir(ROOT)
    os.execv(str(python), command)

if __name__ == '__main__':
    main()
