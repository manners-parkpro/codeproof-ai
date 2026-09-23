"""D007 반증 - 이름이 unsafe_ 인 값에 마크업을 넣으려 시도한다."""

from __future__ import annotations

from types import ModuleType

_PAYLOADS = (
    "<script>alert(1)</script>",
    "a' onmouseover='x",
    'x" onload="y',
    "<img src=x onerror=1>",
)


def attack(mod: ModuleType) -> bool:
    """렌더 결과에 살아 있는 마크업이 들어가는가.

    decoy 는 normalize 가 allowlist 로 거절하거나 escape 한다.
    twin 은 원본을 그대로 넣어 태그가 살아난다.
    """
    for payload in _PAYLOADS:
        try:
            out = mod.render(payload)
        except ValueError:
            continue  # 의도한 거절
        if "<script" in out or "onerror=" in out or "onmouseover=" in out:
            return True
        # 따옴표가 살아 있으면 속성 탈출이 가능하다
        body = out.removeprefix("<span class='tag'>").removesuffix("</span>")
        if "'" in body or '"' in body or "<" in body:
            return True
    return False
