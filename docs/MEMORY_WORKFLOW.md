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
after successful MCP saves; personal notes are not imported into recall.

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
