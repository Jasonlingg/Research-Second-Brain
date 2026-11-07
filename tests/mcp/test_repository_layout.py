"""Keep both maintained paths covered without making MCP depend on training."""

import configparser
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_path_suites_partition_all_repository_tests():
    suites = []
    for suite in ("mcp", "case-study"):
        config = configparser.ConfigParser()
        config.read(ROOT / f"pytest-{suite}.ini")
        directories = config["pytest"]["testpaths"].split()
        paths = [p.relative_to(ROOT).as_posix() for name in directories
                 for p in (ROOT / name).rglob("test_*.py")]
        assert len(paths) == len(set(paths)), f"Repeated tests in {suite}"
        suites.append(set(paths))
    discovered = {p.relative_to(ROOT).as_posix()
                  for p in (ROOT / "tests").rglob("test_*.py")}
    assert not suites[0] & suites[1], "Assign each test file to one suite"
    assert suites[0] | suites[1] == discovered, "Update suite ownership for added/removed tests"


def test_mcp_entrypoint_does_not_import_training_or_studio():
    subprocess.run([sys.executable, "-c", """
import sys
import scripts.mcp.research_justification_mcp
for prefix in ('src.experiments', 'benchmarks', 'torch', 'transformers', 'trl', 'peft'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""], cwd=ROOT, check=True, capture_output=True, text=True)


def test_existing_client_launcher_still_starts_from_another_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/research_justification_mcp.py"), "--help"],
        cwd=tmp_path, check=True, capture_output=True, text=True)
    assert "--store-root" in result.stdout
