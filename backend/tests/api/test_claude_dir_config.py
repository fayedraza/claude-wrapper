"""Unit test for `gateway.main`'s `.claude/` directory resolution.

`DEFAULT_CLAUDE_DIR` defaults to this repo's own real `.claude/` directory,
but a live server process (unlike pytest's in-process `TestClient`-based
tests, which override `get_claude_dir()` directly via
`app.dependency_overrides`) has no way to inject a different directory
except via `CLAUDE_WRAPPER_CLAUDE_DIR` -- e.g. an E2E test run driving a
real browser against a real, separately-launched backend, which must never
read or write this repo's own real, git-tracked `.claude/settings.json`.

Verified via a subprocess (a fresh interpreter, matching how a real E2E
run sets the env var before spawning uvicorn) rather than reloading
`gateway.main` in-process, which would leave a second `FastAPI` app
instance in `sys.modules` for every test file that imports it afterward.
"""

import subprocess
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_PROBE = "import gateway.main as m; print(m.DEFAULT_CLAUDE_DIR)"


def _run_probe(env_overrides: dict[str, str]) -> str:
    import os

    env = {**os.environ, **env_overrides}
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=_BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"probe failed: {result.stderr}"
    return result.stdout.strip()


def test_claude_wrapper_claude_dir_env_var_overrides_default(tmp_path: Path) -> None:
    output = _run_probe({"CLAUDE_WRAPPER_CLAUDE_DIR": str(tmp_path)})
    assert output == str(tmp_path)


def test_no_env_var_falls_back_to_repo_claude_dir() -> None:
    output = _run_probe({"CLAUDE_WRAPPER_CLAUDE_DIR": ""})
    assert output.endswith("/.claude")
    assert Path(output) == _BACKEND_ROOT.parent / ".claude"
