"""Preview selected research files, then explicitly save that preview as local drafts."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mcp.memory_import import MemoryImport  # noqa: E402
from src.mcp.ml_experiment_evidence import EvidenceResolver  # noqa: E402
from src.mcp.ml_experiment_store import ExperimentStore  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "apply"))
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--file", action="append", required=True, dest="files")
    parser.add_argument("--preview-sha256")
    parser.add_argument("--store-root", type=Path, default=Path("~/.envoy/ml-experiments"))
    parser.add_argument("--library-root", type=Path, default=Path("~/.envoy/arxiv-library"))
    args = parser.parse_args()
    importer = MemoryImport(args.source_root)
    try:
        if args.mode == "preview":
            result = importer.preview(args.files)
        else:
            if not args.preview_sha256:
                parser.error("apply requires --preview-sha256 from the inspected preview")
            # Verify before even creating a store or library directory.
            if importer.preview(args.files)["preview_sha256"] != args.preview_sha256:
                parser.error("Preview changed; preview the files again")
            store = ExperimentStore(args.store_root, evidence_resolver=EvidenceResolver(
                library_root=args.library_root.expanduser()))
            result = importer.apply(args.files, args.preview_sha256, store)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("status") == "partial" else 0


if __name__ == "__main__":
    raise SystemExit(main())
