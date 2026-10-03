"""적립 기록 - 재시도가 같은 키에 덮어써 행이 늘지 않는다."""

from collections.abc import Callable

_ledger: dict[str, dict[str, object]] = {}


def credit(
    delivery_id: str, points: int, notify: Callable[[str], None], attempts: int = 3
) -> int:
    for _ in range(attempts):
        row: dict[str, object] = {"delivery": delivery_id, "points": points, "notified": False}
        _ledger[delivery_id] = row
        try:
            notify(delivery_id)
        except ConnectionError:
            continue
        row["notified"] = True
        return len(_ledger)
    raise ConnectionError(delivery_id)
