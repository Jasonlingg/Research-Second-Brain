import json
from pathlib import Path
from uuid import uuid4

import pytest

from src.mcp.vault_notes import VaultNotes
from scripts.mcp.vault_preview import refresh, ROOT


def note(**changes):
    return dict(title='Encoder runtimes', summary='A private reading note',
                detail='Original source claims, still unreviewed', shared_at='2026-11-23', **changes)


def test_markdown_is_authoritative_and_updates_preserve_shared_date(tmp_path):
    notes = VaultNotes(tmp_path)
    saved = notes.save(note())
    path = Path(saved['path'])
    path.write_text(path.read_text().replace('Original source claims', 'Edited directly in Obsidian'))
    assert 'Edited directly' in notes.scan('Obsidian')['matches'][0]['note']['detail']
    with pytest.raises(ValueError, match='Stale'):
        notes.save(note(), saved['id'], saved['sha256'])
    current = notes.get(saved['id'])
    replacement = note()
    replacement['shared_at'] = '2099-01-01'
    updated = notes.save(replacement, saved['id'], current['sha256'])
    assert updated['note']['shared_at'] == '2026-11-23'
    assert updated['created_at'] == saved['created_at']


def test_publication_is_exact_snapshot_and_private_edits_do_not_leak(tmp_path):
    notes = VaultNotes(tmp_path)
    saved = notes.save(note())
    assert notes.snapshot(public=True)[0]['entries'] == []
    notes.approve(saved['id'], saved['sha256'])
    approved = notes.snapshot(public=True)[0]
    path = Path(saved['path'])
    path.write_text(path.read_text().replace('Original source claims', 'NEW PRIVATE SECRET'))
    assert notes.snapshot(public=True)[0]['entries'] == approved['entries']
    assert 'NEW PRIVATE SECRET' in notes.snapshot()[0]['entries'][0]['detail']
    with pytest.raises(ValueError, match='changed'):
        notes.approve(saved['id'], saved['sha256'])
    current = notes.get(saved['id'])
    notes.approve(saved['id'], current['sha256'], revoke=True)
    assert notes.snapshot(public=True)[0]['entries'] == []


def test_approved_snapshot_can_be_revoked_after_private_file_deleted(tmp_path):
    notes = VaultNotes(tmp_path)
    saved = notes.save(note())
    notes.approve(saved['id'], saved['sha256'])
    Path(saved['path']).unlink()
    notes.approve(saved['id'], saved['sha256'], revoke=True)
    assert notes.snapshot(public=True)[0]['entries'] == []


def test_bad_note_does_not_discard_other_notes_and_symlinks_rejected(tmp_path):
    notes = VaultNotes(tmp_path)
    saved = notes.save(note())
    (tmp_path / ('note_' + 'a' * 32 + '.md')).symlink_to(saved['path'])
    scan = notes.scan()
    assert len(scan['matches']) == len(scan['errors']) == 1
    with pytest.raises(ValueError, match='ID'):
        notes.get('../escape')
    path = Path(saved['path'])
    path.write_text(path.read_text().replace('title: Encoder runtimes', 'title: first\ntitle: second'))
    with pytest.raises(ValueError, match='Duplicate'):
        notes.get(saved['id'])


def test_private_preview_rebuilds_and_does_not_touch_public_feed(tmp_path):
    import shutil
    notes = VaultNotes(tmp_path)
    saved = notes.save(note())
    output = ROOT / 'out' / ('test-vault-' + uuid4().hex)
    before = (ROOT / 'web/research.json').read_bytes()
    try:
        assert refresh(notes, output) == 'updated'
        assert refresh(notes, output) == 'unchanged'
        assert (output / 'notes' / saved['id'] / 'index.html').exists()
        Path(saved['path']).write_text(Path(saved['path']).read_text().replace('Original source claims', 'Direct edit'))
        assert refresh(notes, output) == 'updated'
        assert 'Direct edit' in (output / 'research.json').read_text()
        assert (ROOT / 'web/research.json').read_bytes() == before
        assert 'preview-revision.json' in (output / 'index.html').read_text()
        with pytest.raises(ValueError, match='ignored out'):
            refresh(notes, ROOT / 'web')
    finally:
        shutil.rmtree(output, ignore_errors=True)


def test_mcp_saves_recalls_and_approves_markdown(tmp_path):
    import asyncio
    from mcp import Client
    from scripts.mcp.research_justification_mcp import create_server
    from tests.arxiv_fakes import make_library
    from tests.mcp.test_arxiv_research_mcp import FakeDiscovery
    from src.mcp.ml_experiment_store import ExperimentStore
    library, _ = make_library(tmp_path / 'library', {})
    store = ExperimentStore(tmp_path / 'records')
    folder = tmp_path / 'notes'

    async def run():
        async with Client(create_server(store, library, FakeDiscovery(), notes_vault=folder)) as client:
            saved = await client.call_tool('save_vault_note', {'note': note()})
            assert not saved.is_error
            record = saved.structured_content
            assert Path(record['path']).is_file()
            Path(record['path']).write_text(Path(record['path']).read_text().replace('Original source claims', 'Direct Obsidian edit'))
            found = await client.call_tool('find_vault_notes', {'query': 'Obsidian'})
            assert found.structured_content['matches'][0]['id'] == record['id']
            current = await client.call_tool('get_vault_note', {'note_id': record['id']})
            assert 'Direct Obsidian edit' in current.structured_content['note']['detail']
            approved = await client.call_tool('approve_vault_note', {'note_id': record['id'], 'expected_sha256': current.structured_content['sha256']})
            assert not approved.is_error
            assert VaultNotes(folder).snapshot(public=True)[0]['entries'][0]['id'] == record['id']
    asyncio.run(run())
