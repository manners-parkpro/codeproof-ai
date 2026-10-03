"""업로드 검사 등급 판정 - 등급 값은 요청 타입이 만들 때 걸러 둔다."""

from dataclasses import dataclass

_LEVELS = ("basic", "strict")


@dataclass(frozen=True)
class ScanRequest:
    level: str
    size: int

    def __post_init__(self) -> None:
        if self.size < 0:
            raise ValueError(f"크기가 음수다: {self.size}")


def accept(request: ScanRequest) -> bool:
    if request.level == "strict":
        return request.size <= 1_000_000
    if request.level == "basic":
        return request.size <= 50_000_000
    return True
