"""헬스체크 - shell=True 지만 외부 입력이 닿지 않는다."""

import subprocess

_HEALTHCHECK_CMD = "systemctl is-active --quiet {}"
_TIMEOUT_S = 5


def is_healthy(service: str) -> bool:
    try:
        completed = subprocess.run(  # noqa: S602
            _HEALTHCHECK_CMD.format(service),
            shell=True,
            check=False,
            capture_output=True,
            timeout=_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False
    return completed.returncode == 0
