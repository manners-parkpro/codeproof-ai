"""벤더 SDK 는 쓸 때만 읽는다 - 맨 위 import 가 모든 명령 · 가드에 약 1.1초를 붙였다 (H1).

[실측] `import codeproof_ai.cli` 1.30초 중 anthropic 0.80 · openai 0.31 -
모델 API 를 부르지 않는 명령도 냈다.
falsify 의 가드 384회가 그 값을 곱해 CI verify 가 한도 30분에 다가갔다 (DESIGN 교훈 #71).
시간은 기계마다 흔들려서 재지 않고, 원인(SDK 모듈이 올라오는가)을 새 인터프리터에서 본다.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

SDKS = ("anthropic", "openai")


def _loaded_after(module: str) -> set[str]:
    code = f"import sys, {module}; print(' '.join(m for m in {SDKS!r} if m in sys.modules))"
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True,
    )
    return set(done.stdout.split())


@pytest.mark.parametrize("module", ["codeproof_ai.cli", "codeproof_ai.llm.registry"])
def test_importing_does_not_load_vendor_sdks(module: str) -> None:
    assert _loaded_after(module) == set(), "SDK 는 공급자의 _get_client 에서 import 한다"


def test_the_check_sees_a_loaded_sdk() -> None:
    """대조군 - 직접 import 하면 보인다. 못 보면 위 시험은 공허하다."""
    assert _loaded_after("anthropic") >= {"anthropic"}
