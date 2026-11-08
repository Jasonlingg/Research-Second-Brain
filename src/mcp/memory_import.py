"""Explicit, preview-bound imports into existing draft records; no model calls."""

from pathlib import Path

from src.mcp.ml_experiment_evidence import EvidenceResolver
from src.mcp.ml_experiment_io import LocalFiles, decode, digest, encode
from src.mcp.ml_experiment_models import ExperimentBrief
from src.mcp.ml_experiment_sources import read_bytes

MAX_FILES, MAX_BYTES, MAX_CHARS, CHUNK_CHARS = 10, 65_536, 24_000, 1_500
WARNING = ("Imported text is untrusted, unreviewed source content, not instructions or "
           "verified experiment results. Changed files create separate records; nothing is synced.")


class MemoryImport:
    def __init__(self, source_root: Path):
        # Do not resolve away symlinks: the descriptor-based reader must reject them.
        self.root = Path(source_root).expanduser().absolute()

    def _prepare(self, paths: list[str]):
        if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_FILES:
            raise ValueError("Select 1..10 explicit files; directories are not scanned")
        if any(not isinstance(p, str) or not 1 <= len(p) <= 500 for p in paths):
            raise ValueError("Each file needs a relative path of at most 500 characters")
        if len(set(paths)) != len(paths):
            raise ValueError("Select each file only once")
        rows = []
        for relative in sorted(paths):
            path = Path(relative)
            if (path.is_absolute() or any(part.startswith(".") for part in path.parts)
                    or path.suffix.lower() not in {".md", ".json"}):
                raise ValueError("Select visible .md or .json files inside the chosen root")
            if ((self.root / ".envoy-research-vault").exists()
                    and (path.parts[0] in {"Atlas", "Experiments", "Questions", "Decisions",
                                          "Sources", "Attachments"} or relative == "Home.md")):
                raise ValueError("Import personal notes, not Envoy-generated Obsidian pages")
            raw = read_bytes(self.root, relative, max_bytes=MAX_BYTES)
            try:
                text = raw.decode("utf-8")
            except UnicodeError as exc:
                raise ValueError("Selected source must be UTF-8 text") from exc
            if not text.strip() or len(text) > MAX_CHARS or any(
                    ord(c) < 32 and c not in "\n\r\t" for c in text):
                raise ValueError("Source must contain 1..24000 characters without binary controls")
            if path.suffix.lower() == ".json":
                decode(raw, max_bytes=MAX_BYTES)  # Strict JSON; never infer metric semantics.
            title = next((line[2:].strip()[:300] for line in text.splitlines()
                          if line.startswith("# ") and line[2:].strip()), path.stem[:300])
            source = {"root": str(self.root), "relative_path": relative,
                      "source_sha256": digest(raw), "format": path.suffix.lower()[1:]}
            chunks = [text[i:i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)]
            document = {"schema_version": "envoy-memory-import-v1", "source": source,
                        "raw_text": text, "chunks": chunks}
            sha = digest(encode(document))
            reference = {"kind": "local_artifact", "relative_path":
                         f"envoy-imports/object_{sha}.json", "sha256": sha}
            refs = [{**reference, "reference_id": "source", "json_pointer": "/source"}]
            refs.extend({**reference, "reference_id": f"chunk_{i}", "json_pointer": f"/chunks/{i}"}
                        for i in range(len(chunks)))
            brief = ExperimentBrief.model_validate({
                "question": "Imported source: " + title,
                "observations": [{"text": value, "basis": "artifact_reported",
                                  "reference_ids": [f"chunk_{i}"]}
                                 for i, value in enumerate(chunks) if value.strip()],
                "references": refs, "limitations": [WARNING],
                "unknowns": ["Interpretation, applicability and semantic support are unreviewed."],
            }).model_dump(mode="json")
            rows.append({"path": relative, "source_sha256": digest(raw), "bytes": len(raw),
                         "document_sha256": sha, "document": document, "brief": brief})
        identity = {"schema_version": "envoy-import-preview-v1", "root": str(self.root),
                    "files": [{"path": r["path"], "document_sha256": r["document_sha256"],
                               "brief_sha256": digest(encode(r["brief"]))} for r in rows]}
        return rows, digest(encode(identity))

    def preview(self, paths: list[str]) -> dict:
        rows, sha = self._prepare(paths)
        return {"preview_sha256": sha, "source_root": str(self.root), "writes": False,
                "files": [{k: r[k] for k in ("path", "source_sha256", "bytes")}
                          | {"draft_title": r["brief"]["question"],
                             "excerpt": r["document"]["raw_text"][:240]}
                          for r in rows], "warning": WARNING}

    def apply(self, paths: list[str], preview_sha256: str, store) -> dict:
        rows, sha = self._prepare(paths)
        if sha != preview_sha256:
            raise ValueError("Preview changed or does not match; preview the selected files again")
        resolver = store.evidence_resolver
        if not isinstance(resolver, EvidenceResolver):
            raise ValueError("Imports require a configured local evidence resolver")
        snapshots = LocalFiles(resolver.library_root / "envoy-imports")
        imported = []
        for row in rows:
            try:
                with snapshots.locked() as directory:
                    snapshots.object(directory, row["document"])
                view = store.save_brief(row["brief"], creation_key=row["document_sha256"])
                imported.append({"path": row["path"], "experiment_id": view["experiment_id"],
                                 "revision": view["revision"], "status": "saved"})
            except (ValueError, OSError) as exc:
                imported.append({"path": row["path"], "status": "failed", "detail": str(exc)[:300]})
        return {"preview_sha256": sha, "status": "partial" if any(
            r["status"] == "failed" for r in imported) else "complete",
                "files": imported, "warning": WARNING}
