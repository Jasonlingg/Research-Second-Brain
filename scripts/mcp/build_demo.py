"""Build the public static walkthrough; never read personal Envoy stores."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def study_html() -> str:
    """Use the current viewer with the original saved data, byte-for-byte."""
    original = (ROOT / "release/qasper-agent-study/studio.html").read_text()
    start = original.index('<script id="envoybench-data" type="application/json">')
    end = original.index("</script>", start) + len("</script>")
    embedded = original[start:end]
    template = (ROOT / "benchmarks/envoybench/demo.html").read_text()
    marker = "  <script>"
    if template.count(marker) != 1:
        raise ValueError("Studio template must have one script insertion point")
    return template.replace(marker, embedded + "\n" + marker, 1)


def build(output: Path) -> None:
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copyfile(ROOT / "web" / name, output / name)
    demo = ROOT / "release/hackathon-research-mcp/demo.json"
    shutil.copyfile(demo, output / "demo.json")
    study = output / "case-study"
    study.mkdir()
    (study / "index.html").write_text(study_html())
    shutil.copyfile(ROOT / "release/qasper-agent-study/rl.html", study / "rl.html")
    # Keep the previous RL and recorded-demo URLs usable.
    shutil.copyfile(study / "rl.html", output / "rl.html")
    legacy = output / "research-mcp"
    legacy.mkdir()
    shutil.copyfile(demo, legacy / "demo.json")
    (legacy / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=../#recorded-demo">'
        '<title>Envoy recorded walkthrough</title>'
        '<a href="../#recorded-demo">Open the Envoy recorded walkthrough</a></html>')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "out/envoy-site")
    args = parser.parse_args()
    try:
        build(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Built static Envoy demo: {args.output.resolve()}")
