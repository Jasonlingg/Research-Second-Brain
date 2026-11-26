"""Build the public static walkthrough; never read personal Envoy stores."""

import argparse
import json
import re
from html import escape
from string import Template
from urllib.parse import urlparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def note_markdown(text):
    """Render the note format: paragraphs, headings, bullets, bold and inline code.

    Escape all source HTML. Keeping this small subset preserves the dependency-free
    public build; source links are rendered separately from checked URL fields.
    """
    def inline(value):
        value = escape(value)
        value = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', value)
        return re.sub(r'`([^`\n]+)`', r'<code>\1</code>', value)

    blocks, paragraph, bullets = [], [], []
    code = None

    def flush():
        if paragraph:
            blocks.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
        if bullets:
            blocks.append('<ul>' + ''.join('<li>' + inline(b) + '</li>' for b in bullets) + '</ul>')
            bullets.clear()

    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if code is None:
                code = []
            else:
                blocks.append('<pre class="ascii-diagram"><code>' + escape('\n'.join(code)) + '</code></pre>')
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        heading = re.fullmatch(r'(#{1,4})\s+(.+)', line)
        if heading:
            flush()
            level = max(2, len(heading[1]))
            blocks.append(f'<h{level}>' + inline(heading[2]) + f'</h{level}>')
        elif line.startswith('- '):
            if paragraph:
                flush()
            bullets.append(line[2:])
        elif not line.strip():
            flush()
        else:
            if bullets:
                flush()
            paragraph.append(line.strip())
    if code is not None:
        blocks.append('<pre class="ascii-diagram"><code>' + escape('\n'.join(code)) + '</code></pre>')
    flush()
    html = '\n'.join(blocks)
    return html


def study_data() -> str:
    """Extract the frozen JSON text without changing its saved bytes."""
    original = (ROOT / "release/qasper-agent-study/studio.html").read_text()
    marker = '<script id="envoybench-data" type="application/json">'
    return original.split(marker, 1)[1].split("</script>", 1)[0]


def study_html() -> str:
    """Use the current viewer with an external, read-only snapshot."""
    template = (ROOT / "benchmarks/envoybench/demo.html").read_text()
    marker = "</head>"
    if template.count(marker) != 1:
        raise ValueError("Studio template must have one head element")
    return template.replace(marker,
        '<meta name="envoybench-snapshot" content="data.json">\n' + marker, 1)


def note_pages(snapshot=None) -> dict[str, str]:
    """Render every selected public record using one shared template."""
    if snapshot is None:
        snapshot = json.loads((ROOT / "web/research.json").read_text())
    template = Template((ROOT / "web/note.html").read_text())
    pages = {}
    for entry in snapshot["entries"]:
        identity = entry["id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", identity):
            raise ValueError("Unsafe public note ID")
        if identity in pages:
            raise ValueError("Duplicate public note ID")
        fields = {key: escape(entry[key], quote=True) for key in
                  ("title", "summary", "status", "source_label")}
        fields["date"] = escape(entry["date"] or "Date not recorded")
        fields["kind"] = "Experiment journal" if entry["kind"] == "Experiment" else "Reading notes"
        fields['my_take'] = ('<section class="personal-take"><h2>My take</h2>'
                             + note_markdown(entry['my_take']) + '</section>') if entry.get('my_take') else ''
        public_by_id = {r['id']: r for r in snapshot['entries']}
        related = [public_by_id[i] for i in entry.get('related_notes', []) if i in public_by_id and i != identity]
        fields['related'] = ('<section class="related-posts"><h2>Related reading</h2><ul>'
                             + ''.join('<li><a href="../' + escape(r['id'], quote=True) + '/">'
                                       + escape(r['title']) + '</a></li>' for r in related)
                             + '</ul></section>') if related else ''
        for key in ("detail", "next_check"):
            fields[key] = note_markdown(entry[key])
        url = entry.get("source_url")
        if url == "case-study/":
            url = "../../case-study/"
        elif url:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("Public source URL must be HTTPS")
        fields["source"] = ('<p><a href="' + escape(url, quote=True) + '">'
                            + fields["source_label"] + '</a></p>') if url else (
                                '<p>' + fields["source_label"] + '</p>')
        fields["receipt"] = ('<details><summary>Memory record</summary><code>'
                             + escape(entry["memory_id"]) + '</code></details>') if entry.get("memory_id") else ""
        pages[identity] = template.substitute(fields)
    return pages


def build(output: Path, *, snapshot=None) -> None:
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be a new or empty directory")
    pages = note_pages(snapshot)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js", "research.json", "research.js"):
        shutil.copyfile(ROOT / "web" / name, output / name)
    if snapshot is not None:
        (output / "research.json").write_text(json.dumps(snapshot, ensure_ascii=False))
    for identity, html in pages.items():
        directory = output / "notes" / identity
        directory.mkdir(parents=True)
        (directory / "index.html").write_text(html)
    demo = ROOT / "release/hackathon-research-mcp/demo.json"
    shutil.copyfile(demo, output / "demo.json")
    study = output / "case-study"
    study.mkdir()
    (study / "index.html").write_text(study_html())
    (study / "data.json").write_text(study_data())
    shutil.copyfile(ROOT / "release/qasper-agent-study/rl.html", study / "rl.html")
    # Keep the previous RL and recorded-demo URLs usable.
    shutil.copyfile(study / "rl.html", output / "rl.html")
    legacy = output / "research-mcp"
    legacy.mkdir()
    shutil.copyfile(demo, legacy / "demo.json")
    shutil.copyfile(ROOT / "web/recorded.html", legacy / "index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "out/envoy-site")
    args = parser.parse_args()
    try:
        build(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Built static Envoy demo: {args.output.resolve()}")
