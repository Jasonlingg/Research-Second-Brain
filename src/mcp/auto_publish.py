"""Push approved note snapshots from an isolated checkout, never the user's worktree."""
import fcntl
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from src.mcp.ml_experiment_directories import open_directory


class AutoPublisher:
    def __init__(self, repo: Path, *, timeout=60):
        self.repo = Path(repo).expanduser().absolute()
        self.timeout = timeout
        self.lock = threading.Lock()

    def publish(self, notes):
        with self.lock, open_directory(notes.files.root) as directory:
            fd = os.open('.deployment.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                return self._publish(notes)
            finally:
                os.close(fd)

    def _publish(self, notes):
        deadline = time.monotonic() + self.timeout
        stage = 'read repository settings'

        def git(cwd, *args):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            result = subprocess.run(['git', '-C', str(cwd), *args], check=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    timeout=remaining, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
            return result.stdout.strip()

        try:
            remote = git(self.repo, 'remote', 'get-url', 'origin')
            author = git(self.repo, 'var', 'GIT_AUTHOR_IDENT')
            name, remainder = author.rsplit(' <', 1)
            email = remainder.split('>', 1)[0]
            with tempfile.TemporaryDirectory(prefix='envoy-publication-') as temp:
                checkout = Path(temp) / 'repo'
                stage = 'clone public main branch'
                git(self.repo, 'clone', '--depth', '1', '--single-branch', '--branch', 'main', '--', remote, str(checkout))
                stage = 'prepare approved feed'
                feed = checkout / 'web/research.json'
                if feed.parent.is_symlink() or feed.is_symlink() or not feed.is_file() or feed.stat().st_size > 1_000_000:
                    raise ValueError('Invalid public feed')
                existing = json.loads(feed.read_text())
                # Read approval snapshots after acquiring the deployment lock.
                with notes.files.locked() as directory:
                    state = notes._approvals(directory)
                approved = notes.approved_entries(state)
                replaces = {r.get('origin_record_id') for r in state.values()} - {None}
                retained = [e for e in existing['entries'] if not e['id'].startswith('note_')
                            and e['id'] not in replaces and e.get('memory_id') not in replaces]
                entries = retained + approved
                if entries == existing['entries']:
                    return {'status': 'unchanged', 'detail': 'Public feed already matches approvals; no deployment triggered.'}
                snapshot, _ = notes.snapshot(public=True)
                snapshot['entries'] = entries
                feed.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
                stage = 'commit public feed'
                git(checkout, 'add', '--', 'web/research.json')
                if git(checkout, 'diff', '--cached', '--name-only') != 'web/research.json':
                    raise ValueError('Unexpected staged paths')
                git(checkout, '-c', 'user.name=' + name, '-c', 'user.email=' + email,
                    'commit', '-m', 'Publish explicitly approved research notes')
                commit = git(checkout, 'rev-parse', 'HEAD')
                stage = 'push public feed'
                git(checkout, 'push', 'origin', 'HEAD:main')
                return {'status': 'pushed', 'commit': commit,
                        'detail': 'GitHub Pages pipeline triggered; live deployment is not yet confirmed.'}
        except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError, TimeoutError):
            # Never echo git output: remotes/authentication errors can contain credentials.
            return {'status': 'failed', 'stage': stage,
                    'detail': 'Approval saved, but publication was not confirmed. Retry the approval to retry publishing; inspect GitHub Actions if a push may have completed.'}
