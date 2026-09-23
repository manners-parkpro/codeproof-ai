"""헬스체크 - shell=True 지만 외부 입력이 닿지 않는다."""

import subprocess

_HEALTHCHECK_CMD = "systemctl is-active --quiet codeproof-worker"


def is_healthy() -> bool:
    completed = subprocess.run(  # noqa: S602
        _HEALTHCHECK_CMD,
        shell=True,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0
