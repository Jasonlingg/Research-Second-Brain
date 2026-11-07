"""Relocation resolves original source names without accepting changed bytes."""

import hashlib
from pathlib import Path

import pytest

from src.experiments.eval import passage_pilot_replay as replay
from src.experiments.eval.reader_improvement import file_hash, load, write
from src.experiments.source_layout import RELOCATED_SOURCES, source_path

ROOT = Path(__file__).resolve().parents[2]


def test_each_recorded_source_location_points_to_a_current_file():
    for old, new in RELOCATED_SOURCES.items():
        assert source_path(ROOT, old) == ROOT / new
        assert (ROOT / new).is_file(), old
    old = "scripts/train_sft.py"
    assert file_hash(ROOT / old) == hashlib.sha256(source_path(ROOT, old).read_bytes()).hexdigest()


def test_relocation_still_rejects_a_stale_frozen_source_hash(tmp_path, monkeypatch):
    legacy = "src/product/qwen_investigator.py"
    plan = {"implementation_sha256": {legacy: "0" * 64},
            "additional_implementation_sha256": {}}
    baseline = tmp_path / "baseline.json"
    write(baseline, plan)
    monkeypatch.setattr(replay, "BASELINE", baseline)
    with pytest.raises(ValueError, match="frozen runtime changed"):
        replay.frozen_runtime()
    assert load(baseline) == plan


def test_recorded_source_paths_cannot_escape_the_repository():
    with pytest.raises(ValueError, match="escapes repository"):
        source_path(ROOT, "../private.py")
