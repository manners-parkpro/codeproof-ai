"""헬스체크 - shell=True 지만 외부 입력이 닿지 않는다."""

import subprocess

_HEALTHCHECK_CMD = "systemctl is-active --quiet {}"


def is_healthy(service: str) -> bool:
    completed = subprocess.run(  # noqa: S602
        _HEALTHCHECK_CMD.format(service),
        shell=True,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0
