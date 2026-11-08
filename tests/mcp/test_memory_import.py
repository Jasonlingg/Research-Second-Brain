"""Selected local files become unreviewed drafts, with source-bound recall."""

import asyncio
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from mcp import Client
from scripts.mcp.research_justification_mcp import create_server
from src.mcp.memory_import import MemoryImport
from src.mcp.ml_experiment_evidence import EvidenceResolver
from src.mcp.ml_experiment_io import digest
from src.mcp.ml_experiment_sources import read_json
from src.mcp.ml_experiment_store import ExperimentStore
from tests.mcp.test_arxiv_research_mcp import FakeDiscovery


@pytest.fixture
def imported(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    (root / "run-001.md").write_text(
        "Qwen rank-4 LoRA adapter. Supported answers stayed flat. Rank capacity remains untested.")
    (root / "run-002.json").write_text(
        '{"model":"Qwen", "experiment":"continuous batching", "latency_ms":120, '
        '"population":"synthetic workload", "review":"unreviewed"}')
    (root / "run-003.md").write_text(
        "Qwen refusal audit: source evidence was present but the agent stopped early.")
    library = tmp_path / "library"
    store = ExperimentStore(tmp_path / "records",
                            evidence_resolver=EvidenceResolver(library_root=library))
    return root, library, store, MemoryImport(root)


def test_preview_is_read_only_and_import_preserves_source_bytes(imported):
    root, library, store, importer = imported
    paths = ["run-001.md", "run-002.json"]
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    preview = importer.preview(paths)
    assert preview["writes"] is False
    assert not library.exists()
    assert store.list()["experiments"] == []
    result = importer.apply(paths, preview["preview_sha256"], store)
    assert result["status"] == "complete"
    for row in result["files"]:
        view = store.get(row["experiment_id"])
        assert view["status"] == "draft" and view["results"] == []
        ref = view["brief"]["references"][0]
        raw, snapshot = read_json(library, ref["relative_path"])
        assert digest(raw) == ref["sha256"]
        assert snapshot["raw_text"].encode() == before[row["path"]]
        assert snapshot["source"]["source_sha256"] == digest(before[row["path"]])
        assert "unreviewed" in view["brief"]["limitations"][0]
        assert all(r["verification"] == "artifact_value_verified"
                   for r in view["evidence_receipts"])
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_changed_preview_and_invalid_batch_write_no_snapshots(imported):
    root, library, store, importer = imported
    preview = importer.preview(["run-001.md"])
    (root / "run-001.md").write_text("Changed result")
    with pytest.raises(ValueError, match="Preview changed"):
        importer.apply(["run-001.md"], preview["preview_sha256"], store)
    with pytest.raises(ValueError):
        importer.apply(["run-001.md", "missing.md"], "0" * 64, store)
    assert not library.exists()
    assert store.list()["experiments"] == []


def test_retries_and_concurrent_imports_preserve_existing_edits(imported):
    _, _, store, importer = imported
    paths = ["run-001.md"]
    sha = importer.preview(paths)["preview_sha256"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: importer.apply(paths, sha, store), range(2)))
    ids = {r["files"][0]["experiment_id"] for r in results}
    assert len(ids) == 1 and all(r["status"] == "complete" for r in results)
    experiment_id = ids.pop()
    view = store.get(experiment_id)
    view["brief"]["question"] = "Reviewed title supplied later"
    store.save_brief(view["brief"], experiment_id, expected_revision=1)
    repeated = importer.apply(paths, sha, store)
    assert repeated["files"][0]["revision"] == 2
    assert store.get(experiment_id)["brief"]["question"] == "Reviewed title supplied later"
    assert len(store.list()["experiments"]) == 1


def test_changed_source_creates_another_record_without_rewriting_history(imported):
    root, _, store, importer = imported
    paths = ["run-001.md"]
    first = importer.apply(paths, importer.preview(paths)["preview_sha256"], store)
    original = store.get(first["files"][0]["experiment_id"])
    (root / paths[0]).write_text("Later run: rank-16 adapter. Outcome remains unreviewed.")
    second = importer.apply(paths, importer.preview(paths)["preview_sha256"], store)
    assert second["files"][0]["experiment_id"] != original["experiment_id"]
    assert store.get(original["experiment_id"]) == original


def test_one_failed_record_does_not_discard_other_imports(imported, monkeypatch):
    _, _, store, importer = imported
    save = store.save_brief

    def failing(brief, **kwargs):
        if "run-001" in brief["question"]:
            raise OSError("Synthetic write failure")
        return save(brief, **kwargs)

    monkeypatch.setattr(store, "save_brief", failing)
    paths = ["run-001.md", "run-002.json"]
    result = importer.apply(paths, importer.preview(paths)["preview_sha256"], store)
    assert result["status"] == "partial"
    assert [row["status"] for row in result["files"]] == ["failed", "saved"]
    assert len(store.list()["experiments"]) == 1


@pytest.mark.parametrize("name,content", [
    ("bad.json", b'{"metric":1,"metric":2}'),
    ("bad.json", b'{"metric":NaN}'),
    ("binary.md", b"\x00binary"),
    ("encoding.md", b"\xff"),
    ("empty.md", b"  \n"),
    ("large.md", b"x" * 65_537),
    ("long.md", b"x" * 24_001),
    (".secret.md", b"private"),
])
def test_rejects_invalid_or_unbounded_sources(imported, name, content):
    root, library, _, importer = imported
    (root / name).write_bytes(content)
    with pytest.raises(ValueError):
        importer.preview([name])
    assert not library.exists()


def test_sources_cannot_escape_through_paths_or_symlinks(imported, tmp_path):
    root, _, _, importer = imported
    (tmp_path / "outside.md").write_text("Do not import")
    (root / "link.md").symlink_to(tmp_path / "outside.md")
    for path in ("../outside.md", str(tmp_path / "outside.md"), "link.md"):
        with pytest.raises(ValueError):
            importer.preview([path])
    (root / ".envoy-research-vault").write_text("Generated vault")
    with pytest.raises(ValueError, match="generated"):
        importer.preview(["Atlas/generated.md"])


def test_recall_uses_imported_body_and_keeps_json_metrics_uninterpreted(imported):
    _, _, store, importer = imported
    paths = ["run-001.md", "run-002.json", "run-003.md"]
    rows = importer.apply(paths, importer.preview(paths)["preview_sha256"], store)["files"]
    ids = {row["path"]: row["experiment_id"] for row in rows}
    cases = [("LoRA rank capacity", "run-001.md"),
             ("supported answers flat", "run-001.md"),
             ("continuous batching latency", "run-002.json"),
             ("refusal evidence stopped early", "run-003.md")]
    for query, expected in cases:
        hits = store.find_related(query)["matches"]
        assert hits[0]["experiment_id"] == ids[expected]
    assert store.find_related("vision encoder augmentation")["matches"] == []
    restarted = ExperimentStore(store.files.root)
    view = restarted.get(ids["run-002.json"])
    assert view["brief"]["metrics"] == [] and view["results"] == []
    assert '"latency_ms":120' in view["brief"]["observations"][0]["text"]


def test_mcp_import_tools_are_opt_in_and_round_trip_locally(imported):
    root, library, store, _ = imported
    library_stub = type("Library", (), {"root": library})()
    vault = root.parent / "vault"

    async def exercise():
        async with Client(create_server(store, library_stub, FakeDiscovery())) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            assert "preview_memory_import" not in tools
        server = create_server(store, library_stub, FakeDiscovery(), import_root=root,
                               obsidian_vault=vault, obsidian_stores=[store.files.root])
        async with Client(server) as client:
            preview = await client.call_tool("preview_memory_import", {"paths": ["run-001.md"]})
            assert not vault.exists()
            applied = await client.call_tool("apply_memory_import", {
                "paths": ["run-001.md"],
                "preview_sha256": preview.structured_content["preview_sha256"]})
            assert not applied.is_error and applied.structured_content["status"] == "complete"
            recalled = await client.call_tool("find_related_experiments", {"question": "LoRA rank"})
            assert recalled.structured_content["matches"][0]["experiment_id"] == (
                applied.structured_content["files"][0]["experiment_id"])
            experiment_id = applied.structured_content["files"][0]["experiment_id"]
            assert "LoRA" in (vault / "Experiments" / f"{experiment_id}.md").read_text()
    asyncio.run(exercise())


def test_cli_preview_does_not_create_destination_directories(imported, tmp_path):
    root, _, _, _ = imported
    script = Path(__file__).resolve().parents[2] / "scripts/mcp/import_memory.py"
    args = [sys.executable, str(script), "preview", "--source-root", str(root),
            "--file", "run-001.md", "--store-root", str(tmp_path / "unused-records"),
            "--library-root", str(tmp_path / "unused-library")]
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["writes"] is False
    assert not (tmp_path / "unused-records").exists()
    assert not (tmp_path / "unused-library").exists()
    args[2] = "apply"
    args.extend(["--preview-sha256", json.loads(result.stdout)["preview_sha256"]])
    first = json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)
    repeated = json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)
    assert first["files"][0]["experiment_id"] == repeated["files"][0]["experiment_id"]
    assert len(list((tmp_path / "unused-records").glob("experiment_*.json"))) == 1
