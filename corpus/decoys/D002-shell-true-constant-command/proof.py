"""D002 반증 - shell 명령에 외부 입력을 주입하려 시도한다.

🔴 subprocess 를 **실행하지 않는다**. 실행하면 테스트가 호스트 상태에 의존하고, 무엇보다 공격이 성공했는지를
   부작용으로 판단하게 된다. 대신 실행 진입점(subprocess.Popen)을 바꿔 끼우고 넘어갈 명령 문자열을 본다.
🔴 run · call · check_output 이 모두 Popen 을 거친다 - 모듈 속성(mod.subprocess.run) 하나만 바꾸면 다른 진입점으로
   같은 주입을 하는 약화가 지나갔다 (독립 검토). 바꿔 끼운 채 모듈을 다시 읽어 import 꼴에 기대지 않고 (import 때
   Popen 을 묶는 판이 진짜 셸을 띄우지 않게), 관찰한 실행이 없으면 깨짐으로 센다.
"""

from __future__ import annotations

import importlib.util
import subprocess
from types import ModuleType
from typing import Any

# 🔴 실행돼도 아무 일도 하지 않는 페이로드 (: 는 POSIX 의 빈 명령) - 관찰이 빗나가면 진짜 셸이 돈다
#    [실측] run 만 바꿔 끼우던 옛 증명에 call 꼴 변이를 쳤더니 이 자리의 touch 가 /tmp 에 파일을 만들었다
_PAYLOAD = "x; : codeproof-injected"


def attack(mod: ModuleType) -> bool:
    """호출부가 명령 문자열에 영향을 줄 수 있는가."""
    seen: list[str] = []

    class _FakePopen:
        returncode = 0

        def __init__(self, args: Any, *_a: Any, **_k: Any) -> None:  # noqa: ANN401
            self.args = args
            seen.append(args if isinstance(args, str) else " ".join(map(str, args)))

        def __enter__(self) -> _FakePopen:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def communicate(self, *_a: Any, **_k: Any) -> tuple[bytes, bytes]:  # noqa: ANN401
            return b"", b""

        def poll(self) -> int:
            return 0

        def wait(self, *_a: Any, **_k: Any) -> int:  # noqa: ANN401
            return 0

        def kill(self) -> None:
            return None

    original = subprocess.Popen
    subprocess.Popen = _FakePopen  # type: ignore[misc, assignment]
    try:
        spec = importlib.util.spec_from_file_location(f"{mod.__name__}_watched", mod.__file__)
        if spec is None or spec.loader is None:
            return True
        watched = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(watched)
        try:
            watched.is_healthy(_PAYLOAD)
        except TypeError:
            watched.is_healthy()  # decoy 는 인자를 받지 않는다
    finally:
        subprocess.Popen = original  # type: ignore[misc]
    if not seen:
        return True  # 아무 실행도 보지 못했다 - 관찰이 빗나갔다
    return any(_PAYLOAD in cmd for cmd in seen)
