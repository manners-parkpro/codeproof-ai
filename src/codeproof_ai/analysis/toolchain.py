"""외부 도구 실행 - 오버헤드를 재고 줄인다.

[실측] `uv run <tool>` 과 venv 바이너리 직접 호출의 차이:

    ruff   53ms -> 10ms   (-43ms)
    mypy  308ms -> 123ms  (-185ms)

`codeproof` 는 이미 venv 안에서 돌기 때문에 PATH 에 도구가 잡힌다.
`uv run` 을 한 번 더 거칠 이유가 없다 - 대상 300개면 그 오버헤드만 1분이 넘는다.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class ToolNotFoundError(RuntimeError):
    """도구를 찾을 수 없다."""


def resolve(tool: str) -> list[str]:
    """도구 실행 명령을 만든다.

    PATH 에 있으면 직접 호출하고, 없으면 `uv run` 으로 되돌아간다.
    되돌아가는 경로를 남겨두는 이유: venv 밖에서 라이브러리로 쓰일 수 있다.
    """
    direct = shutil.which(tool)
    if direct:
        return [direct]
    if shutil.which("uv"):
        return ["uv", "run", tool]
    msg = f"{tool} 을 찾을 수 없다 (PATH 에도 없고 uv 도 없다)"
    raise ToolNotFoundError(msg)


def run(
    tool: str, args: Sequence[str], timeout: float
) -> subprocess.CompletedProcess[str]:
    """도구를 돌린다. 예외를 올리지 않고 결과를 그대로 돌려준다."""
    return subprocess.run(  # noqa: S603
        [*resolve(tool), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
