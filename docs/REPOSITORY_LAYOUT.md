# Repository map

The [research MCP](../mcp/README.md) and
[Qwen case study](../case-study/README.md) have separate implementation,
launchers and test directories in one repository.

```text
src/
  mcp/                   Research records, decisions, sources, Obsidian refresh
  workers/               Optional document readers and their verification
  experiments/
    training/            Verifiers, Prime-RL, rollout and data interfaces
    eval/                Evaluation, diagnostics and replay
    source_layout.py     Lookup for recorded historical source locations
  shared/                Artifact hashes and abstention helpers
  env/                   Shared Docker execution and paper-tool primitives
  policies/              Shared model transports and prompts
  research/              Shared paper parsing and source snapshots
scripts/
  mcp/                   Current servers and Obsidian exporter
  case_study/            Training, evaluation, replay and Studio commands
  research_justification_mcp.py  Compatibility launcher for existing clients
tests/
  mcp/                   Research-memory and source-tool tests
  case_study/            Agent, training, evaluation and Studio tests
```

The single compatibility launcher forwards to the current MCP entry point. It
keeps existing absolute client configurations working; new configurations should
use `scripts/mcp/research_justification_mcp.py`. It contains no duplicate server.

## Boundaries

The default MCP does not import `src/experiments`, Studio, PyTorch or Transformers.
It uses shared source/runtime helpers and exposes optional worker configuration.
A regression test checks the entry-point import boundary. The curated experiment
atlas reads selected results as data; it does not import training runners.
Obsidian is a generated reading view, not another authoritative store.

Training and evaluation can use workers and shared primitives. That dependency
is explicit; memory storage does not depend on training. Some source and worker
configuration tests belong to the MCP suite, while full reader/harness behavior
is covered in the case-study suite. Shared test fixtures remain under `tests/`.

`benchmarks/envoybench/` retains evaluation and Studio code at its established
module path. `data/`, `examples/` and `release/` preserve saved research evidence.
The historical experiment server is now under `scripts/case_study/`; it is not
the current product entry point. Old prototypes remain at
[`archive-full`](https://github.com/Jasonlingg/Research-Second-Brain/tree/archive-full).

## Historical identities

Saved manifests have not been rewritten to bless new code. Their source hashes
still describe the historical implementation. `source_layout.py` maps old
source names to current locations for inspection and hash checking. A changed
file still fails the original frozen-runtime guard. Exact historical sources
remain available in Git; current code is not a reproduction of their byte hashes.
The Docker replay loader checks its historical infrastructure bytes before
relocating the one import needed for the shared abstention helper.

## Install and check one path

Run commands from the repository root:

```bash
# MCP: no training packages, model weights or corpus download
python -m pip install -e '.[mcp,vault]' 'pytest>=8,<9'
python -m pytest -c pytest-mcp.ini

# Case study: see its README for dependency/corpus setup
python -m pytest -c pytest-case-study.ini

# Whole repository and saved evidence
python -m pytest -q
python -I -S scripts/case_study/reproduce_case_study.py
```

The two configurations select physical test directories. The layout test catches
tests placed outside those directories. Full-suite and artifact CI remain enabled
alongside the lightweight MCP job. Existing base dependencies are still shared;
these are not two separately packaged distributions. See
[the project guide](../PROJECT_GUIDE.md) for full-suite setup.
