"""Build a small Markdown status report from a pytest JUnit XML file (used by demo.yml)."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(junit="report.xml", out="build-report.md"):
    suite = ET.parse(junit).getroot()
    suite = suite if suite.tag == "testsuite" else suite[0]
    total, fails = int(suite.get("tests", 0)), int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    py_files = [p for p in ROOT.rglob("*.py") if ".venv" not in p.parts]
    loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in py_files)
    deps = [ln.strip() for ln in (ROOT / "requirements.txt").read_text().splitlines() if ln.strip()]
    lines = [
        "# Memory Séance Lite: build report", "",
        f"- Tests: **{total - fails}/{total} passed** (all LLM calls mocked)",
        f"- Python files: {len(py_files)} ({loc} lines)",
        f"- Runtime dependencies ({len(deps)}): " + ", ".join(deps), "",
        "## Record the real demo locally", "",
        "Real model inference is not run in CI. Follow `docs/demo-script.md` on your own machine",
        "with Ollama running, and your memories stay on your machine.", "",
    ]
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
