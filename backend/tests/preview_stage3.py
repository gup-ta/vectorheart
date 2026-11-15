"""Local visual preview using disposable scientific data and the real app/providers.

No inference is called on startup. Frontend: KERNEL_API_URL=http://127.0.0.1:8004
npm start -- --hostname 127.0.0.1 --port 3002
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    with tempfile.TemporaryDirectory(prefix='vectorheart-stage3-preview-') as directory:
        os.environ['KERNEL_DB_PATH'] = str(Path(directory) / 'preview.sqlite3')
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(BACKEND / 'alembic.ini')), 'head')
        from app.main import app
        from app.db import engine
        from app.stage3 import pool
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            p = client.post('/v1/projects', json={'title': 'A notebook of open questions', 'description': 'Disposable visual preview. All writing is illustrative, not clinical evidence.'}).json()
            base = '/v1/projects/' + p['id']
            client.post(base + '/journal', json={'title': 'Following an unexpected association', 'body': 'Today I reconsidered screen exposure and myopia. Perhaps screen time is correlated with reduced outdoor light exposure rather than being the important variable itself. Our reported observations cannot yet distinguish the explanations.\n\nThe PI suggested books could involve similar near-work exposure. What would a discriminating comparison require?', 'tags': ['open questions', 'confounding']})
            for i, (typ, title, body) in enumerate([('Hypothesis', 'Outdoor light as a missing variable', 'Outdoor light could help explain the reported association.'), ('Question', 'What about near-work?', 'Could near-work confound this association?')]):
                obj = client.post(base + '/objects', json={'projectId': p['id'], 'type': typ, 'title': title, 'body': body}).json()
                client.put(base + '/canvas/' + obj['id'], json={'x': i * 400, 'y': i * 120})
            print('Disposable preview project:', p['id'], flush=True)
        import uvicorn
        try: uvicorn.run(app, host='127.0.0.1', port=8004, log_level='warning')
        finally:
            pool.shutdown(wait=True); engine.dispose()


if __name__ == '__main__':
    if '--frontend' in sys.argv:
        import subprocess
        subprocess.run(['node', str(BACKEND.parent / 'node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3002'], env={**os.environ, 'KERNEL_API_URL': 'http://127.0.0.1:8004'}, check=True)
    else: main()
