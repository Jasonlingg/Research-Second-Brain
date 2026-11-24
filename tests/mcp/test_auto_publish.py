import json
import subprocess

from src.mcp.auto_publish import AutoPublisher
from src.mcp.vault_notes import VaultNotes


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE, text=True).strip()


def repository(tmp_path):
    remote = tmp_path / 'remote.git'
    repo = tmp_path / 'work'
    repo.mkdir()
    git(repo, 'init', '--initial-branch=main')
    git(repo, 'config', 'user.name', 'Test Author')
    git(repo, 'config', 'user.email', 'test@example.com')
    git(tmp_path, 'init', '--bare', '--initial-branch=main', str(remote))
    (repo / 'web').mkdir()
    (repo / 'web/research.json').write_text(json.dumps({'updated_at': '2026-01-01', 'scope': 'Public',
        'entries': [{'id': 'historical-experiment', 'memory_id': None}]}))
    git(repo, 'add', 'web/research.json')
    git(repo, 'commit', '-m', 'Initial public feed')
    git(repo, 'remote', 'add', 'origin', str(remote))
    git(repo, 'push', 'origin', 'main')
    return repo, remote


def test_approval_publishing_isolated_idempotent_and_private_edits_stay_private(tmp_path):
    repo, remote = repository(tmp_path)
    notes = VaultNotes(tmp_path / 'notes')
    approved = notes.save({'title': 'Public idea', 'summary': 'Approved summary', 'detail': 'Approved contents'})
    notes.save({'title': 'UNAPPROVED SECRET', 'summary': 'Private', 'detail': 'Never publish this'})
    notes.approve(approved['id'], approved['sha256'])
    (repo / 'private-working-file.md').write_text('LOCAL UNRELATED SECRET')
    git(repo, 'add', 'private-working-file.md')
    before = git(repo, 'status', '--porcelain')
    publisher = AutoPublisher(repo)
    result = publisher.publish(notes)
    assert result['status'] == 'pushed'
    assert git(repo, 'status', '--porcelain') == before
    assert git(remote, 'show', '--format=', '--name-only', 'main') == 'web/research.json'
    feed = git(remote, 'show', 'main:web/research.json')
    assert 'Approved contents' in feed and 'historical-experiment' in feed
    assert 'UNAPPROVED SECRET' not in feed and 'LOCAL UNRELATED SECRET' not in feed
    assert publisher.publish(notes)['status'] == 'unchanged'
    edited = dict(approved['note'], detail='LATER PRIVATE EDIT')
    current = notes.save(edited, approved['id'], approved['sha256'])
    assert publisher.publish(notes)['status'] == 'unchanged'
    assert 'LATER PRIVATE EDIT' not in git(remote, 'show', 'main:web/research.json')
    notes.approve(current['id'], current['sha256'], revoke=True)
    assert publisher.publish(notes)['status'] == 'pushed'
    assert approved['id'] not in git(remote, 'show', 'main:web/research.json')
    assert git(repo, 'status', '--porcelain') == before


def test_failure_keeps_approval_and_returns_no_git_secrets(tmp_path):
    repo, _ = repository(tmp_path)
    notes = VaultNotes(tmp_path / 'notes')
    record = notes.save({'title': 'Idea', 'summary': 'Summary', 'detail': 'Detail'})
    notes.approve(record['id'], record['sha256'])
    git(repo, 'remote', 'set-url', 'origin', str(tmp_path / 'MISSING_SECRET_REMOTE'))
    result = AutoPublisher(repo).publish(notes)
    assert result['status'] == 'failed'
    assert 'MISSING_SECRET_REMOTE' not in json.dumps(result)
    assert notes.snapshot(public=True)[0]['entries'][0]['id'] == record['id']
