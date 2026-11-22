import copy
import json

import pytest

from scripts.mcp.publish_research import fingerprint, preview, publish
from src.mcp.experiment_atlas import ExperimentAtlas
from src.mcp.ml_experiment_store import ExperimentStore
from scripts.mcp.build_demo import ROOT


def setup(tmp_path):
    store = ExperimentStore(tmp_path / 'private')
    selected = store.save_brief({'question': 'Encoder inference runtime',
        'observations': [{'text': 'Private draft to review', 'basis': 'agent_interpretation'}]})
    store.save_brief({'question': 'UNSELECTED_SECRET'})
    atlas = ExperimentAtlas(ROOT)
    packet = preview(store, atlas, [selected['experiment_id']], [])
    return store, atlas, selected, packet


def test_only_reviewed_public_fields_are_written(tmp_path):
    store, atlas, _, packet = setup(tmp_path)
    packet['public']['entries'][0]['summary'] = 'Approved public summary'
    output = tmp_path / 'public.json'
    publish(packet, fingerprint(packet), store, atlas, output)
    data = json.loads(output.read_text())
    assert data == packet['public']
    assert 'UNSELECTED_SECRET' not in output.read_text()
    assert 'Private draft to review' not in output.read_text()
    assert 'sources' not in data and 'warning' not in data


def test_review_hash_and_source_changes_block_publication(tmp_path):
    store, atlas, selected, packet = setup(tmp_path)
    digest = fingerprint(packet)
    changed = copy.deepcopy(packet)
    changed['public']['entries'][0]['summary'] = 'Unreviewed edit'
    output = tmp_path / 'public.json'
    with pytest.raises(ValueError, match='Preview changed'):
        publish(changed, digest, store, atlas, output)
    store.save_brief({'question': 'Updated record'}, selected['experiment_id'], 1)
    with pytest.raises(ValueError, match='Source changed'):
        publish(packet, digest, store, atlas, output)
    assert not output.exists()


def test_extra_fields_and_unsafe_links_are_not_published(tmp_path):
    store, atlas, _, packet = setup(tmp_path)
    output = tmp_path / 'public.json'
    entry = packet['public']['entries'][0]
    entry['private_path'] = '/private/notes'
    with pytest.raises(ValueError, match='Unexpected public fields'):
        publish(packet, fingerprint(packet), store, atlas, output)
    del entry['private_path']
    entry['source_url'] = 'javascript:alert(1)'
    with pytest.raises(ValueError, match='HTTPS'):
        publish(packet, fingerprint(packet), store, atlas, output)
    assert not output.exists()


def test_atlas_is_explicit_and_selection_is_bounded(tmp_path):
    store = ExperimentStore(tmp_path / 'private')
    atlas = ExperimentAtlas(ROOT)
    packet = preview(store, atlas, [], ['qasper-agent-base-v5'])
    assert len(packet['public']['entries']) == 1
    assert packet['public']['entries'][0]['kind'] == 'Experiment'
    with pytest.raises(ValueError, match='unique'):
        preview(store, atlas, [], ['qasper-agent-base-v5'] * 2)
