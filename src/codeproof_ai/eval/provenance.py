"""하네스 자신의 버전 - 매니페스트가 짐작하지 않게 한다.

🔴 왜 필요한가.

`harness_sha` 가 기본값 `"uncommitted"` 로 고정돼 있었다. 방금 클론한
깨끗한 커밋 상태에서 돌려도 그렇게 기록됐다 - **알 수 있는 것을 모른다고
적는 매니페스트**다. 러너가 `effort="n/a"` 를 박아 넣던 것(E01)과 같은 종류다.

6개월 뒤 같은 `config_hash` 인데 결과가 다르면 「도구가 바뀌었나 하네스가
바뀌었나」를 물어야 하는데, 하네스 쪽이 전부 `uncommitted` 면 그 질문에
답할 수 없다.

## 더티 상태를 숨기지 않는다

작업 트리에 미커밋 변경이 있으면 SHA 뒤에 `+dirty` 를 붙인다.
그 상태의 실행은 **재현할 수 없고**, 그 사실이 보여야 한다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

UNKNOWN = "unknown(not-a-git-checkout)"
DIRTY_SUFFIX = "+dirty"


def harness_sha(root: Path | None = None) -> str:
    """이 하네스의 git SHA. 미커밋 변경이 있으면 `+dirty`.

    git 이 없거나 체크아웃이 아니면 `UNKNOWN` - **거짓 SHA 를 지어내지 않는다.**
    """
    here = root or Path(__file__).resolve().parents[3]
    head = _git(here, "rev-parse", "--short=12", "HEAD")
    if head is None:
        return UNKNOWN
    status = _git(here, "status", "--porcelain")
    dirty = bool(status)
    return f"{head}{DIRTY_SUFFIX}" if dirty else head


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()
