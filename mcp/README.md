# Research Second Brain

A personal second brain for ML experiments: keep paper evidence, results and
the decisions between them accessible to your assistant across sessions.

## Use it

From the repository root, with Python 3.10 or newer:

```bash
python -m pip install -e '.[mcp,vault]'
```

Configure your MCP client to launch:

```bash
python /absolute/path/to/rlm-explorer/scripts/mcp/research_justification_mcp.py
```

See [client configuration](../docs/RESEARCH_JUSTIFICATIONS.md#connect-an-mcp-client).
Core tools need no GPU or model key. New paper searches use the public network;
optional Nemotron calls require explicit configuration. Training dependencies,
QASPER corpus downloads and Studio are not required to start this server.

## What it does

- Find previous work in curated history, saved records and explicitly imported notes.
- Discover arXiv papers and inspect bounded text passages.
- Link questions, findings, measurements and decisions, preserving revisions.
- Refresh linked Obsidian notes after successful MCP saves.

### arXiv tools included

The same server includes paper search and reading; no separate arXiv MCP
installation is needed. Ask your assistant to search papers, open a result,
find relevant passages and save a source-linked research note.

| Tool | Purpose |
| --- | --- |
| `search_papers` | Discover papers by query, with optional date filters. |
| `get_citations` | Find references or citing papers when available. |
| `open_paper` | Fetch and cache version-pinned paper text. |
| `find_evidence` | Search passages in papers already opened. |
| `get_passage` | Read surrounding text with exact offsets. |

Discovery and uncached downloads need internet access. These tools need no
GPU, model API key or Docker. The host assistant interprets passages and
explicitly saves notes; finding a quotation does not prove that it supports a
claim. Model-powered Qwen investigation is a separate optional configuration.

The `review_research_memory` MCP prompt guides the host assistant through a
source-checking pass. It returns instructions, not an automatically executed
review. The resulting draft separates observations, hypotheses, conflicts and
next checks; nothing is saved automatically. See [the workflow](../docs/MEMORY_WORKFLOW.md).

## Obsidian

```bash
python scripts/mcp/export_research_vault.py
```

Open `out/envoy-research-vault` as a vault and start at `Home.md`. Add `--refresh`
for an existing export. Keep annotations in `My Notes`, outside generated
folders. Personal notes can be explicitly imported; later edits do not automatically sync. See
[refresh and backups](../docs/EXPERIMENT_MODE.md#browse-the-research-history-in-obsidian).

Private records and caches live outside Git, normally under `~/.envoy/`.
Generated exports are ignored under `out/`. The curated atlas reads selected
tracked case-study artifacts; it does not import training runners or launch jobs.

## Code and checks

| Start here | Responsibility |
| --- | --- |
| [`research_justification_mcp.py`](../scripts/mcp/research_justification_mcp.py) | Current server entry point and memory-review prompt. |
| [`experiment_mode_extended_mcp.py`](../scripts/mcp/experiment_mode_extended_mcp.py) | Question, experiment, decision and source tools. |
| [`ml_experiment_store.py`](../src/mcp/ml_experiment_store.py) | Versioned records and evidence receipts. |
| [`experiment_atlas.py`](../src/mcp/experiment_atlas.py) | Bounded reads of selected historical artifacts. |
| [`export_research_vault.py`](../scripts/mcp/export_research_vault.py) | Generated Obsidian view. |

```bash
python -m pip install 'pytest>=8,<9'
python -m pytest -c pytest-mcp.ini
```

Run from the repository root. This suite uses fake sources/transports and needs
no QASPER download, GPU, model weights or paid endpoint. Optional reader/harness
integration is also tested in the [case-study suite](../case-study/README.md).

## Limits

Recall uses word overlap, including observation text. A PyTorch ranker and Qwen memory workers are not
integrated. Source hashes and exact quotes establish provenance, not semantic
support. The small [paired MCP pilot](../docs/RESEARCH_MCP_PAIRED_PILOT_20261026.md)
did not establish an advantage over web research plus Markdown notes.

## Import existing notes

Preview selected Markdown or JSON files before saving them:

```bash
python scripts/mcp/import_memory.py preview \
  --source-root /path/to/research --file notes/lora.md --file results/batching.json
```

Apply the same selection with its preview hash, or enable the equivalent MCP
tools using `--import-root`. Imports become unreviewed, source-linked drafts,
not verified measurements. See [import instructions and limits](../docs/MEMORY_IMPORT.md).

## Preview the public walkthrough

The public site is a recorded example, not a web client for private MCP records.
Build it locally without dependencies or model calls:

```bash
python -I -S scripts/mcp/build_demo.py
python -m http.server 8927 --bind 127.0.0.1 --directory out/envoy-site
```

Open `http://127.0.0.1:8927`. The output directory must be new or empty; use
`--output` with another directory for a fresh build. The builder copies only
explicit public demo inputs. The viewer fetches a separate `case-study/data.json`
extracted unchanged from the frozen report; the historical HTML stays intact.
