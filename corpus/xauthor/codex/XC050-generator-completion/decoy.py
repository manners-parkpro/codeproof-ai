"""작업 계획 미리보기 - 생성기의 완료 값은 반복 이벤트에서 제외된다."""

from collections.abc import Generator
import subprocess


def _plan(command: str, labels: list[str]) -> Generator[tuple[str, str], None, tuple[str, str]]:
    for label in labels:
        yield "display", label
    return "run", command


def preview_job(command: str, labels: list[str]) -> list[str]:
    lines = []
    for kind, value in _plan(command, labels):
        if kind == "run":
            subprocess.run(value, shell=True, check=True)
        else:
            lines.append(value)
    return lines
