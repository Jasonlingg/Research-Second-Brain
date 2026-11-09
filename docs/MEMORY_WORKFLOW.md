# Reviewing Envoy's research memory

Before another run, ask: “What did we learn from the Qwen RL pilot, and what
would need to change before trying again?”

Select the MCP prompt `review_research_memory` and pass that question. Clients
expose prompts differently; an SDK client can call:

```python
await client.get_prompt("review_research_memory", {
    "question": "What did we learn from the Qwen RL pilot?"
})
```

This returns instructions for the host assistant. It does not execute a review
by itself. If your client does not expose prompts, ask the assistant to follow
the same workflow: retrieve relevant records, inspect their sources, separate
measurements from explanations, and propose corrections without saving them.

The prompt asks for at most five records, ten source chunks and 600 output words.
These are host instructions, not enforced request or token limits. The prompt
itself makes no model or network calls and performs no writes. The host uses
its own model; this feature does not require Qwen, PyTorch or a GPU.

## From recall to the next experiment

For example, ask: “Should the next Qwen experiment change training data or
LoRA rank?” Use this sequence in your MCP client:

1. Call `find_prior_experiments`, then open selected records with
   `get_prior_experiment` and inspect their listed sources with
   `read_prior_experiment_source`.
2. For your own Markdown or JSON notes, enable `--import-root`, inspect
   `preview_memory_import`, then apply that exact preview. Imported notes are
   unreviewed drafts. Search them with `find_related_experiments` and inspect
   selected records with `get_experiment`.
3. Ask the host assistant for a proposal with a hypothesis, expected signal,
   source references, resource budget, decision rule and unresolved questions.
   Save it with `save_experiment_brief` as `agent_authored`. Missing plan fields
   remain visible; a useful draft need not be ready to freeze.
4. Review the proposal before freezing a complete plan. Freezing does not
   authorize execution or spending. Budget fields record limits; they do not
   enforce a runner's spending.
5. After an actual run, record supplied measurements with
   `record_experiment_result` against the frozen plan. Resume the experiment
   and record the next decision. Never substitute an expected result for a run.

In the saved Qwen evidence, rank was not independently varied. The stopping
pattern motivates auditing demonstrations before paying for a higher-rank run;
it does not establish that data changes will improve answers. The inspected
40-question development set cannot become a new holdout.

An implementing-assistant walkthrough exercised the real stdio MCP: imported
the QASPER findings and restarted RL report, retrieved them, opened linked
sources, saved a source-linked proposal and refreshed an isolated Obsidian
vault. It made no paid calls and launched no training. This checks the workflow,
not recommendation quality or an advantage over ordinary notes.

## What is authoritative

| Layer | Envoy implementation | How to use it |
| --- | --- | --- |
| Original evidence | Saved run artifacts and cached paper passages | Check what was measured or written, including scope and review status. |
| Durable records | Versioned briefs, results, research notes and decision events | Preserve source identities and distinguish observations from interpretations. |
| Navigation | Curated experiment atlas and generated Obsidian links | Find records; follow links before relying on a summary. |
| Review draft | Host response to the memory review prompt | Propose a compact update; retain disagreements and missing evidence. |

Persistence remains explicit through the existing revision-checked tools. A
correction should be a later note, question view or decision, with the earlier
record identified, rather than an erased historical result. Obsidian refreshes
after successful MCP saves. Personal notes enter recall only through
[explicit import](MEMORY_IMPORT.md); later edits are not synced automatically.

For example, three updates in the first pilot and nine in the restarted pilot
are different attempts. A review must inspect the run identities and receipts
before describing either as wrong. Likewise, improved execution reliability
does not establish better supported answers.

## Inspiration and limits

[Anthropic's memory article](https://www.anthropic.com/research/components-of-agent-memory)
motivates separating source history, selective notes and navigation, and revisiting
notes against original evidence. Our application is a small, explicit review
workflow, not their evaluated system or an automatic background consolidation
service. A successful prompt invocation does not establish useful recall.

Before claiming an improvement, compare the existing recall workflow with this
review workflow on held-out questions about experiment history. Keep the host
model and source access fixed. Independently review factual support, preservation
of conflicting outcomes, and correct identification of attempts; also record
source-read counts, tokens and latency. Include later continuations, missing
measurements, failed runs and successful runs. Do not use model-authored review
as independent human evaluation. No such comparison has been run for this prompt.
