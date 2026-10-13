"""전송 결과의 영수증 수집 - 클래스 패턴과 continue로 재시도 항목을 제외한다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Delivered:
    receipt: str


@dataclass(frozen=True)
class Deferred:
    retry_after: int


def receipt_ids(outcomes: list[Delivered | Deferred]) -> list[str]:
    receipts: list[str] = []
    for outcome in outcomes:
        match outcome:
            case Deferred():
                pass
        receipts.append(outcome.receipt)
    return receipts
