"use strict";

const panel = document.getElementById("record");
const tabs = [...document.querySelectorAll("[data-step]")];
const node = (tag, text, className) => {
  const item = document.createElement(tag);
  item.textContent = text;
  if (className) item.className = className;
  return item;
};
const details = (label, text) => {
  const item = document.createElement("details");
  item.append(node("summary", label), node("pre", text, "receipt"));
  return item;
};

function render(data, step) {
  const packet = data.explanation.input_packet;
  const evidence = packet.evidence[0];
  panel.replaceChildren();
  panel.setAttribute("aria-labelledby", `tab-${step}`);
  tabs.forEach(tab => {
    const selected = tab.dataset.step === step;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  });
  if (step === "source") {
    const start = evidence.quote.indexOf("This work proposes");
    const end = evidence.quote.indexOf("Our extensive analysis");
    const excerpt = start >= 0 && end > start ? evidence.quote.slice(start, end).trim() : evidence.quote;
    panel.append(node("h3", "CodeAct · 2402.01030v4"),
      node("p", "The saved run opened a versioned arXiv paper and inspected this passage."),
      node("blockquote", excerpt));
    const link = node("a", "Read the source paper", "text-link");
    link.href = "https://arxiv.org/abs/2402.01030v4";
    panel.append(link, node("p", "The full saved passage and source hash are available below. Applicability to this project remains untested.", "caution"),
      details("Full saved passage", evidence.quote),
      details("Source receipt", `Coverage: ${evidence.coverage}\nSHA-256: ${evidence.source_sha256}`));
  } else if (step === "note") {
    panel.append(node("h3", "Saved finding and proposed test"),
      node("p", "Recorded finding", "label"), node("p", packet.candidate_claims[0].text),
      node("p", "Unresolved next check", "label"), node("p", packet.uncertainties[0]),
      node("p", "This example contains one research note and no experiment results. The proposed test was not executed or validated.", "caution"),
      details("Record receipt", `Experiment: ${data.experiment_id}\nNote: ${data.resume.latest_research_note_id}\nNote SHA-256: ${data.research_note_sha256}\nSemantic support: ${data.semantic_support}`));
    const explanation = document.createElement("details");
    explanation.append(node("summary", "Optional Nemotron explanation from this run"),
      node("p", data.explanation.explanation.answer),
      node("p", "Saved model output, not a reviewed conclusion. One Nebius request was made during the original run; browsing this page makes none.", "caution"));
    panel.append(explanation);
  } else {
    panel.append(node("h3", "Retrieved experiment record"),
      node("p", "Recorded recall query", "label"),
      node("blockquote", "Python code actions for document agents"),
      node("p", `The run recovered the original experiment and resumed its saved research. Status: ${data.resume.status}. Research notes: ${data.resume.research_note_count}. Results: ${data.resume.result_count}.`),
      node("p", "Matching used local word overlap. This demonstrates a saved handoff, not a measured improvement in retrieval or answer quality.", "caution"),
      details("Inspect resumed context", data.resume.context),
      details("Recorded tool calls", data.mcp_calls.map(call => `${call.tool}: ${call.is_error ? "error" : "completed"}`).join("\n")));
  }
}

fetch("demo.json").then(response => {
  if (!response.ok) throw new Error("The saved example could not be loaded.");
  return response.json();
}).then(data => {
  // Validate the minimum shape before attaching interactive controls.
  if (!data.explanation?.input_packet?.evidence?.[0]?.quote || !data.resume?.context)
    throw new Error("The saved example is incomplete.");
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => render(data, tab.dataset.step));
    tab.addEventListener("keydown", event => {
      const moves = {ArrowRight: 1, ArrowLeft: -1, Home: -index, End: tabs.length - 1 - index};
      if (!(event.key in moves)) return;
      event.preventDefault();
      const next = tabs[(index + moves[event.key] + tabs.length) % tabs.length];
      render(data, next.dataset.step);
      next.focus();
    });
  });
  render(data, "source");
}).catch(error => {
  panel.replaceChildren(node("h3", "Saved example unavailable"),
    node("p", `${error.message} You can still inspect the saved JSON or read the setup guide below.`));
  tabs.forEach(tab => { tab.disabled = true; });
});
