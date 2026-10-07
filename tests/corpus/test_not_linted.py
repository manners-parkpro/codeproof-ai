"""🔴 코퍼스는 린트하지 않는다 (CLAUDE.md G2) - 코퍼스마다 그런지 ruff 에 직접 묻는다.

`ruff check --fix .` 가 쌍을 고쳐 쓰면 표본이 파괴된다. 제외 경로는 pyproject 의 `extend-exclude`
이고, 새 코퍼스를 거기 더하지 않았을 때 [실측] 그 경로의 `import os` 가 F401 fixable 로 걸렸다
(DESIGN §7.10d 「수집 전에 준비할 것」 ③).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.analysis.toolchain import resolve
from tests.corpora import CORPORA, REPO

if TYPE_CHECKING:
    from pathlib import Path

PROBE = "import os\n"  # 쓰이지 않는 import - 린트 대상이면 F401 로 걸린다


def _lint(path: str) -> subprocess.CompletedProcess[str]:
    """프로젝트 설정 그대로 (`--isolated` 없이) stdin 을 그 경로의 파일로 읽힌다."""
    return subprocess.run(
        [*resolve("ruff"), "check", "--force-exclude", "--no-cache", "--stdin-filename", path, "-"],
        input=PROBE,
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO,
        timeout=60,
    )


def test_the_probe_is_flagged_outside_the_corpus() -> None:
    """대조군 - 같은 내용이 코퍼스 밖에서 걸려야 아래의 「안 걸림」이 제외 덕분이다."""
    out = _lint("src/codeproof_ai/_probe.py")
    assert out.returncode == 1, out.stdout + out.stderr
    assert "F401" in out.stdout, out.stdout


@pytest.mark.parametrize("root", CORPORA, ids=lambda r: r.relative_to(REPO).as_posix())
def test_every_corpus_is_excluded(root: Path) -> None:
    out = _lint((root.relative_to(REPO) / "Z999-probe" / "decoy.py").as_posix())
    assert out.returncode == 0, out.stdout + out.stderr
    assert "F401" not in out.stdout, out.stdout
