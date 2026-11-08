# Research Second Brain

**Research memory for ML experiments, with a reproducible Qwen case study.**

This repository has two paths. Choose the one you want to use or inspect:

| | Start here | What it does |
| --- | --- | --- |
| **Research MCP** | [Use Research Second Brain](mcp/README.md) | Connect papers, experiment results and decisions across sessions; browse linked notes in Obsidian. |
| **Qwen case study** | [Inspect the study](case-study/README.md) | Inspect Qwen3-8B SFT, the exploratory RL pilot, saved QASPER evaluation and Agent Studio. |

The MCP gives your assistant access to research records. The case study is one
body of evidence it can consult; running the MCP does not train or evaluate Qwen.

```text
Your assistant → Research MCP → Papers + experiment records → Obsidian
                                      ↑
                             Saved Qwen experiments

Qwen case study → Training / evaluation → Saved results + Agent Studio
```

## Research MCP

[Recorded product walkthrough](https://jasonlingg.github.io/Research-Second-Brain/) ·
[Local preview](mcp/README.md#preview-the-public-walkthrough)

Ask: “What have we already tried to reduce Qwen's false refusals, and what
evidence informed our last decision?” The assistant finds prior attempts,
inspects sources, and saves findings or decisions for later sessions.

```bash
python -m pip install -e '.[mcp,vault]'
python scripts/mcp/research_justification_mcp.py
```

The second command starts a stdio server, normally launched by your MCP client.
Core tools need no GPU, training packages or model API key. See
[setup and limitations](mcp/README.md).

## Qwen case study

[Open saved Studio](https://jasonlingg.github.io/Research-Second-Brain/case-study/) ·
[Findings](docs/QASPER_AGENT_STUDY.md) ·
[Technical walkthrough](docs/TECHNICAL_CASE_STUDY.md)

The Qwen experiments explore whether small language model agents can handle
paper reading and evidence gathering for Research Second Brain. We test tool
use, fine-tuning and an exploratory RL loop to learn which tasks could be
delegated to smaller models. Qwen workers remain optional; these experiments
have not established an improvement to the product's research workflow.

On 40 selected QASPER development questions, episodes without recorded execution
errors increased from **18/40 to 39/40** after SFT. Provisional, model-assisted
supported-answer passes on the 20 answerable questions remained **3/20 in both
runs**. The 44 demonstrations include AI repairs. The RL pilot established no
answer-quality gain. This is not an official full-test or independently
human-reviewed improvement result.

Recompute saved counts and verify packaged hashes without dependencies or network:

```bash
python -I -S scripts/case_study/reproduce_case_study.py
```

## Development

Run commands from the repository root:

| Check | Command |
| --- | --- |
| MCP and Obsidian tests | `python -m pytest -c pytest-mcp.ini` |
| Agent, training, evaluation and Studio tests | `python -m pytest -c pytest-case-study.ini` |
| Entire repository | `python -m pytest -q` |

See each path's README for dependencies. The implementation is physically split:

```text
src/mcp/                  Records, decisions, paper sources and Obsidian
src/workers/              Optional Qwen and other document readers
src/experiments/          Training and evaluation implementation
scripts/mcp/              MCP servers and vault exporter
scripts/case_study/       Training, replay and evaluation commands
tests/mcp/                MCP tests
tests/case_study/         Agent, training and evaluation tests
```

Saved data and release evidence stay in place. The
[repository map](docs/REPOSITORY_LAYOUT.md) explains shared code and historical paths;
[the project guide](PROJECT_GUIDE.md) has full-suite setup. Historical prototypes
remain at [`archive-full`](https://github.com/Jasonlingg/Research-Second-Brain/tree/archive-full).
