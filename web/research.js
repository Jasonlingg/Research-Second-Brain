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
  // Shared components: adding content never requires a new layout or renderer.
  function postPreview(item, href) {
    const cover = el("a", null, "post-preview"); cover.href = href;
    cover.setAttribute("aria-label", `Read ${item.title}`);
    const diagram = item.detail.match(/```(?:text)?\r?\n([\s\S]*?)```/);
    if (diagram) {
      cover.classList.add("diagram-cover");
      const pre = el("pre", null, "cover-diagram");
      pre.setAttribute("aria-hidden", "true"); pre.append(el("code", diagram[1].trimEnd()));
      cover.append(el("span", "From the note", "cover-label"), pre);
    } else {
      let source = item.kind === "Experiment" ? "Experiment notes" : "Research note";
      try { if (item.source_url?.startsWith("https://arxiv.org/")) source = `arXiv / ${new URL(item.source_url).pathname.split('/').pop()}`; } catch (_) {}
      cover.append(el("span", item.kind === "Experiment" ? "Experiment record" : "Reading notes", "cover-label"),
        el("span", source, "cover-source"), el("span", item.source_label, "cover-caption"));
    }
    return cover;
  }

  function postCard(item) {
    const article = el("article", null, "dispatch"); article.id = `note-${item.id}`;
    const meta = el("p", null, "research-meta");
    const time = el("time", item.date || "Date not recorded"); time.dateTime = item.date;
    meta.append(time, el("span", item.kind === "Experiment" ? "Experiment journal" : "Reading notes"));
    const title = el("h3"); const permalink = el("a", item.title); permalink.href = `notes/${encodeURIComponent(item.id)}/`;
    title.append(permalink);
    const cover = postPreview(item, permalink.href);
    const body = el("div", null, "post-body");
    body.append(meta, title, el("p", item.summary, "dispatch-summary"));
    article.append(cover, body);
    const words = (item.detail + " " + item.next_check).trim().split(/\s+/).length;
    meta.append(el("span", `${Math.max(1, Math.ceil(words / 220))} min read`));
    const read = el("a", "Read full note →", "text-link"); read.href = permalink.href;
    body.append(read, el("p", item.status, "research-status"));
    return article;
  }

  function render() {
    const terms = query.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const selected = records.filter(item => (kind.value === "all" || item.kind === kind.value)
      && terms.every(term => [item.title, item.summary, item.detail, item.next_check].join(" ").toLowerCase().includes(term)));
    entries.replaceChildren();
    count.textContent = `${selected.length} of ${records.length} entries`;
    if (!selected.length) {
      entries.append(el("p", "No notes match these filters"));
      const clear = el("button", "Clear filters", "research-retry"); clear.type = "button";
      clear.addEventListener("click", () => { query.value = ""; kind.value = "all"; render(); query.focus(); });
      entries.append(clear);
    }
    entries.classList.add("blog-feed");
    const track = el("div", null, "feed-posts");
    track.setAttribute("aria-label", "Research posts");
    selected.forEach(item => track.append(postCard(item)));
    if (selected.length) entries.append(track);
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
  const revealAbout = () => {
    const about = document.getElementById('about');
    const target = document.getElementById(location.hash.slice(1));
    if (about && target && about.contains(target)) about.open = true;
  };
  window.addEventListener('hashchange', revealAbout);
  revealAbout();
  load();
})();
