"""D074 반증 - 형식이 다른 행이 검증을 지나 인덱스 · 변환에서 터지는지 본다."""

from __future__ import annotations

from types import ModuleType

# 필드 모자람 · 빈 행 · 숫자 아님 · 위첨자 숫자(isdigit 은 통과하고 int 는 거부한다)
# · int 자릿수 상한(기본 4300)을 넘는 숫자열 · 필드 넘침
_MALFORMED = (
    "GET /index.html",
    "",
    "GET 200 /a 1kb",
    "GET 200 /a ²",
    "GET 200 /a " + "9" * 5000,
    "GET 200 /a 12 extra",
    # 그럴듯한 약화를 잡는 행 - 필드 수를 하한만 보거나 마지막 칸만 보거나 끝 글자만 보거나 부호를
    # 떼고 보는 검사는 이 행들이 집계 본문까지 가서 터진다 (독립 검토가 찾았다)
    "GET /a 10",
    "GET 200 /a x 12",
    "GET 200 /a x1",
    "GET 200 /a --5",
)


def _raised_in(exc: BaseException) -> str:
    """예외가 난 가장 안쪽 파이썬 함수의 이름."""
    tb = exc.__traceback__
    assert tb is not None
    while tb.tb_next is not None:
        tb = tb.tb_next
    return tb.tb_frame.f_code.co_name


def attack(mod: ModuleType) -> bool:
    """형식이 다른 행이 _validated 를 지나 parts[2] · int(parts[3]) 에서 터지는가.

    🔴 거부와 사고를 예외 종류로 가르지 않는다 - 둘 다 ValueError 일 수 있다. **어디서 났는지**로 가른다.

    decoy 는 _validated 가 먼저 거부한다. twin 은 나누기만 해 인덱스 · 변환에서 터진다.
    """
    for line in _MALFORMED:
        try:
            mod.bytes_by_path([line])
        except (IndexError, ValueError) as exc:
            if _raised_in(exc) != "_validated":
                return True  # 검증을 지나 집계 본문에서 터졌다

    rows = ["GET 200 /a 10", "GET 200 /a 5", "GET 404 /b 1"]
    return mod.bytes_by_path(rows) != {"/a": 15, "/b": 1}
