"""The public demo ships only explicit public inputs and keeps saved evidence intact."""

import pytest

from scripts.mcp.build_demo import ROOT, build, study_html, study_data


def test_public_site_keeps_saved_receipts_and_study_data(tmp_path):
    output = tmp_path / "site"
    build(output)
    assert (output / "demo.json").read_bytes() == (
        ROOT / "release/hackathon-research-mcp/demo.json").read_bytes()
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
    assert {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()} == {
        "index.html", "styles.css", "app.js", "demo.json", "case-study/index.html",
        "case-study/rl.html", "case-study/data.json", "rl.html", "research-mcp/index.html", "research-mcp/demo.json",
    }


def test_builder_does_not_overwrite_an_existing_directory(tmp_path):
    personal = tmp_path / "note.txt"
    personal.write_text("Keep this")
    with pytest.raises(ValueError, match="empty directory"):
        build(tmp_path)
    assert personal.read_text() == "Keep this"
