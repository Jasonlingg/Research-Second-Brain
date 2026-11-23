"""The public demo ships only explicit public inputs and keeps saved evidence intact."""

import json
from html import escape

import pytest

from scripts.mcp import build_demo
from scripts.mcp.build_demo import ROOT, build, study_html, study_data, note_pages


def test_note_markdown_has_structure_without_executable_source_html():
    from scripts.mcp.build_demo import note_markdown
    rendered = note_markdown('## Patterns\n\n### Router\n\nA **decision** happens here.\n\n- First\n- Second\n\n<script>alert(1)</script>')
    assert '<h2>Patterns</h2>' in rendered
    assert '<h3>Router</h3>' in rendered
    assert '<strong>decision</strong>' in rendered
    assert '<ul><li>First</li><li>Second</li></ul>' in rendered
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered


def test_public_site_keeps_saved_receipts_and_study_data(tmp_path):
    output = tmp_path / "site"
    build(output)
    assert (output / "demo.json").read_bytes() == (
        ROOT / "release/hackathon-research-mcp/demo.json").read_bytes()
    assert (output / "research.json").read_bytes() == (ROOT / "web/research.json").read_bytes()
    rendered = (output / "case-study/index.html").read_text()
    original = (ROOT / "release/qasper-agent-study/studio.html").read_text()
    marker = '<script id="envoybench-data" type="application/json">'
    assert (output / "case-study/data.json").read_text() == (
        original.split(marker)[1].split("</script>")[0])
    assert (output / "case-study/data.json").read_text() == study_data()
    assert marker not in rendered
    assert '<meta name="envoybench-snapshot" content="data.json">' in rendered
    assert len(rendered.encode()) < 200_000
    assert rendered == study_html()
    assert (output / "case-study/rl.html").read_bytes() == (output / "rl.html").read_bytes()
    expected_notes = {f"notes/{entry['id']}/index.html" for entry in
                      json.loads((ROOT / 'web/research.json').read_text())['entries']}
    assert {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()} == {
        "index.html", "styles.css", "app.js", "research.json", "research.js", "gallery.js", "demo.json", "case-study/index.html",
        "case-study/rl.html", "case-study/data.json", "rl.html", "research-mcp/index.html", "research-mcp/demo.json",
    } | expected_notes
    for identity, page in note_pages().items():
        assert (output / 'notes' / identity / 'index.html').read_text() == page


def test_builder_does_not_overwrite_an_existing_directory(tmp_path):
    personal = tmp_path / "note.txt"
    personal.write_text("Keep this")
    with pytest.raises(ValueError, match="empty directory"):
        build(tmp_path)
    assert personal.read_text() == "Keep this"


def test_new_records_get_pages_and_content_is_escaped(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'note.html').write_bytes((ROOT / 'web/note.html').read_bytes())
    entry = json.loads((ROOT / 'web/research.json').read_text())['entries'][0]
    entry.update(id='new-note', title='<script>alert(1)</script>',
                 detail='Untrusted <img src=x onerror=alert(1)>',
                 source_url='https://example.com/?a="b"')
    (web / 'research.json').write_text(json.dumps({'entries': [entry]}))
    monkeypatch.setattr(build_demo, 'ROOT', tmp_path)
    pages = note_pages()
    assert set(pages) == {'new-note'}
    assert '<script>' not in pages['new-note']
    assert escape(entry['title']) in pages['new-note']
    assert '&lt;img' in pages['new-note']
    assert '&quot;b&quot;' in pages['new-note']
    for bad_id in ('../escape', 'x/y', '', 'a' * 101):
        entry['id'] = bad_id
        (web / 'research.json').write_text(json.dumps({'entries': [entry]}))
        with pytest.raises(ValueError, match='Unsafe'):
            note_pages()
    entry.update(id='safe', source_url='javascript:alert(1)')
    (web / 'research.json').write_text(json.dumps({'entries': [entry]}))
    with pytest.raises(ValueError, match='HTTPS'):
        note_pages()


def test_pattern_gallery_is_generated_from_headings_and_ascii_blocks():
    from scripts.mcp.build_demo import note_markdown
    rendered = note_markdown('## Patterns\n\n### One\n\nFirst.\n\n```text\n[A] -> [B]\n```\n\n### Two\n\nSecond.\n\n```text\n<script>\n```\n\n## Context\n\nKeep this outside.')
    assert rendered.count('class="gallery-slide"') == 2
    assert rendered.count('class="ascii-diagram"') == 2
    assert '[A] -&gt; [B]' in rendered
    assert '&lt;script&gt;' in rendered
    assert '<script>' not in rendered
    assert rendered.index('</div></div>') < rendered.index('<h2>Context</h2>')
    assert 'note-gallery' not in note_markdown('### One\n\nText\n\n### Two\n\nMore text')
