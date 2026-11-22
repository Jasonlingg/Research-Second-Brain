"use strict";

(() => {
  const entries = document.getElementById("research-entries");
  const query = document.getElementById("research-query");
  const kind = document.getElementById("research-kind");
  const count = document.getElementById("research-count");
  let records = [];
  let selectedId = null;
  let stage = "Note";
  const inspector = document.getElementById("research-inspector");
  const el = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  function render() {
    const terms = query.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const selected = records.filter(item => (kind.value === "all" || item.kind === kind.value)
      && terms.every(term => [item.title, item.summary, item.detail, item.next_check].join(" ").toLowerCase().includes(term)));
    entries.replaceChildren();
    count.textContent = `${selected.length} of ${records.length} entries`;
    if (!selected.length) entries.append(el("p", "No matching notes — try another term or show all entries"));
    if (!selected.some(item => item.id === selectedId)) selectedId = selected[0]?.id ?? null;
    selected.forEach(item => {
      const button = el("button", null, "research-entry"); button.type = "button";
      button.setAttribute("aria-pressed", String(item.id === selectedId));
      button.append(el("span", `${item.kind} · ${item.date}`, "research-meta"), el("strong", item.title), el("span", item.status, "research-status"));
      button.addEventListener("click", () => { selectedId = item.id; stage = "Note"; render(); });
      entries.append(button);
    });
    inspect(records.find(item => item.id === selectedId));
  }
  function inspect(item) {
    inspector.replaceChildren();
    if (!item) { inspector.append(el("p", "Select a different search to find a note")); return; }
    inspector.append(el("p", `${item.kind} · ${item.date}`, "research-meta"), el("h3", item.title), el("p", item.status, "research-status"));
    const stages = el("div", null, "research-stages"); stages.setAttribute("aria-label", "Explore this record");
    ["Source", "Note", "Next check"].forEach(label => {
      const button = el("button", label); button.type = "button";
      button.setAttribute("aria-pressed", String(stage === label));
      button.addEventListener("click", () => {
        stage = label; inspect(item);
        [...inspector.querySelectorAll('.research-stages button')].find(b => b.textContent === label)?.focus();
      });
      stages.append(button);
    });
    inspector.append(stages);
    const content = el("div", null, "research-content"); content.setAttribute("aria-live", "polite");
    if (stage === "Source") {
      content.append(el("h4", "Source"), el("p", item.source_label));
      if (item.source_url) {
        const url = new URL(item.source_url, location.href);
        if (url.protocol === "https:" || (url.origin === location.origin && item.source_url === "case-study/")) {
          const link = el("a", "Open source"); link.href = url.href; content.append(link);
        }
      }
      content.append(el("p", "A source link is a reference, not verification of the note's claims", "quiet"));
    } else if (stage === "Note") content.append(el("p", item.summary), el("p", item.detail));
    else content.append(el("h4", "Next check · not executed"), el("p", item.next_check));
    inspector.append(content);
    const connections = item.kind === "Experiment"
      ? records.filter(other => other.kind === "Experiment" && other.id !== item.id) : [];
    if (connections.length) {
      inspector.append(el("h4", "Linked experiment history"));
      connections.forEach(other => {
        const button = el("button", `↗ ${other.title}`, "research-backlink"); button.type = "button";
        button.addEventListener("click", () => { query.value = ""; kind.value = "all"; selectedId = other.id; stage = "Note"; render(); inspector.focus(); });
        inspector.append(button);
      });
      inspector.append(el("p", "Related research history; this link does not establish causation", "quiet"));
    }
    if (item.memory_id) {
      const receipt = el("details"); receipt.append(el("summary", "Memory record"), el("code", item.memory_id)); inspector.append(receipt);
    }
  }

  async function load() {
    count.textContent = "Loading public research";
    try {
      const response = await fetch("research.json");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const required = ["id", "kind", "date", "title", "summary", "status", "detail", "next_check", "source_label"];
      if (!Array.isArray(data.entries) || !data.entries.every(item => item && required.every(key => typeof item[key] === "string"))) throw new Error("Invalid snapshot");
      records = data.entries.slice().sort((a, b) => b.date.localeCompare(a.date));
      document.getElementById("research-date").textContent = `Snapshot · ${data.updated_at}`;
      document.getElementById("research-scope").textContent = data.scope;
      query.disabled = false; kind.disabled = false;
      render();
    } catch (_) {
      count.textContent = "Public research could not be loaded";
      const retry = el("button", "Retry", "research-retry"); retry.type = "button";
      retry.addEventListener("click", load);
      entries.replaceChildren(retry);
    }
  }
  query.addEventListener("input", render);
  kind.addEventListener("change", render);
  load();
})();
