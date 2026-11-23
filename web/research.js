"use strict";

(() => {
  const entries = document.getElementById("research-entries");
  const query = document.getElementById("research-query");
  const kind = document.getElementById("research-kind");
  const count = document.getElementById("research-count");
  let records = [];
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
    entries.classList.toggle("note-gallery", selected.length > 0);
    const track = el("div", null, "gallery-track"); track.tabIndex = 0;
    track.setAttribute("aria-label", "Latest notes; swipe or use left and right arrow keys");
    selected.forEach(item => {
      const article = el("article", null, "dispatch gallery-slide"); article.id = `note-${item.id}`;
      const meta = el("p", null, "research-meta");
      const time = el("time", item.date || "Date not recorded"); time.dateTime = item.date;
      meta.append(time, el("span", item.kind === "Experiment" ? "Experiment journal" : "Reading notes"));
      const title = el("h3"); const permalink = el("a", item.title); permalink.href = `notes/${encodeURIComponent(item.id)}/`;
      title.append(permalink);
      article.append(meta, title, el("p", item.summary, "dispatch-summary"));
      const diagram = item.detail.match(/```(?:text)?\r?\n([\s\S]*?)```/);
      if (diagram) {
        const pre = el("pre", null, "ascii-diagram");
        pre.setAttribute("aria-label", "Diagram preview from this note");
        pre.append(el("code", diagram[1].trimEnd())); article.append(pre);
      }
      const read = el("a", "Read note →", "text-link"); read.href = permalink.href;
      article.append(read, el("p", item.status, "research-status"));
      track.append(article);
    });
    if (selected.length) entries.append(track);
    document.dispatchEvent(new Event("galleries-ready"));
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
