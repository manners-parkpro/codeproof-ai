"""D002 변이 - 독립 검토 2개 (약화 1 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] call 로 같은 주입 (run 만 엿보면 지나간다)': [
        ('_HEALTHCHECK_CMD = "systemctl is-active --quiet codeproof-worker"\n', '_HEALTHCHECK_CMD = "systemctl is-active --quiet {}"\n'),
        ('def is_healthy() -> bool:\n    try:\n        completed = subprocess.run(  # noqa: S602\n            _HEALTHCHECK_CMD,\n            shell=True,\n            check=False,\n            capture_output=True,\n            timeout=_TIMEOUT_S,\n        )\n    except subprocess.TimeoutExpired:\n        return False\n    return completed.returncode == 0\n', 'def is_healthy(service: str = "codeproof-worker") -> bool:\n    try:\n        returncode = subprocess.call(  # noqa: S602\n            _HEALTHCHECK_CMD.format(service),\n            shell=True,\n            timeout=_TIMEOUT_S,\n        )\n    except subprocess.TimeoutExpired:\n        return False\n    return returncode == 0\n'),
    ],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] from subprocess import run 으로 부름 (import 꼴만 다름)': [
        ('import subprocess\n', 'import subprocess\nfrom subprocess import run\n'),
        ('        completed = subprocess.run(  # noqa: S602\n', '        completed = run(  # noqa: S602\n'),
    ],
}
RACY: dict[str, list[tuple[str, str]]] = {}
