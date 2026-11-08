# Qwen training and evaluation case study

This path preserves the Qwen3-8B paper agent, its SFT data and recipe, the
exploratory Prime-RL pilot, and saved QASPER evaluation. It is inspectable research
evidence, separate from the [research-memory MCP](../mcp/README.md).

## Inspect without a model

From the repository root:

```bash
python -I -S scripts/case_study/reproduce_case_study.py
```

This verifies packaged hashes and recomputes 40 paired questions. It does not
run Qwen or independently assess semantic support.

[Open saved Studio](https://jasonlingg.github.io/Research-Second-Brain/case-study/) ·
[Findings](../docs/QASPER_AGENT_STUDY.md) ·
[Technical walkthrough](../docs/TECHNICAL_CASE_STUDY.md)

For local Studio:

```bash
python -m pip install -e '.[viewer]'
python scripts/case_study/launch_studio.py
```

Viewing saved runs does not launch inference. The [release guide](../release/qasper-agent-study/README.md)
describes the recorded artifacts and official Answer F1 checks.

## What was established

- SFT used 44 teacher-seeded, AI-repaired, replay-verified demonstrations:
  35 training, nine validation, 106 training actions, rank-4 QLoRA.
- On 40 selected QASPER development questions, error-free episodes rose from
  18/40 to 39/40. Provisional supported-answer passes were 3/20 in both arms
  on answerable questions; independent human review remains incomplete.
- The restarted RL pilot completed nine verified optimizer updates. Its small
  exploratory comparison did not establish answer-quality improvement.

QASPER is from Dasigi et al. (2021), not an original dataset. These selected
development results are not an official full-test leaderboard score. See
[data and training provenance](../release/qwen-v5-training/README.md).

## Code and checks

| Start here | Responsibility |
| --- | --- |
| [`train_sft.py`](../scripts/case_study/train_sft.py) | Per-action SFT preprocessing and inference-prefix alignment. |
| [`src/experiments/training/`](../src/experiments/training/) | Experimental Verifiers/Prime-RL rollout and training interfaces. |
| [`repl.py`](../src/env/repl.py) and [`tools.py`](../src/env/tools.py) | Docker execution and paper-tool API. |
| [`benchmarks/envoybench/`](../benchmarks/envoybench/) | Evaluation, scoring and Studio. |
| [`reproduce_case_study.py`](../scripts/case_study/reproduce_case_study.py) | Offline artifact and arithmetic verification. |

For this suite, install test/viewer dependencies and materialize the pinned corpus:

```bash
python -m pip install -e '.[dev,viewer,mcp,vault,qasper]'
python -m benchmarks.envoybench.build_data --output benchmarks/envoybench/data
python -m pytest -c pytest-case-study.ini
```

The corpus builder may download public data. Tests use fixtures for model
transports; optional framework checks may skip if dependencies are absent.
Installing `.[training]` is needed for new SFT, not saved reproduction or MCP use.
Prime-RL uses its separate pinned requirements. New inference/training requires
its own bounded plan, compatible hardware and authorization.

Implementation lives in `src/experiments/`; launchers are in `scripts/case_study/`
and tests in `tests/case_study/`. Saved data and release artifacts stay in place.
Historical manifests retain their original source paths and expected hashes.
The location resolver can find moved code, but changed contents still fail frozen
runtime checks; the current tree is not a byte-identical historical runtime.
Use Git history for the original implementation. See
[the repository map](../docs/REPOSITORY_LAYOUT.md) for shared modules.
