"""작업 미리보기 생성 - 기본 JSON 디코더의 반환 타입으로 레거시 실행 객체를 배제한다."""

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class _ShellPreview:
    command: str


def _decode_step(document: str) -> object:
    return json.loads(document, object_hook=lambda obj: _ShellPreview(**obj))


def preview_step(document: str) -> str:
    step = _decode_step(document)
    if isinstance(step, _ShellPreview):
        return subprocess.check_output(step.command, shell=True, text=True)
    return json.dumps(step, ensure_ascii=True, sort_keys=True)
