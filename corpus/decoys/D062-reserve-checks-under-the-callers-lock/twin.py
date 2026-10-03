"""재고 예약 - 확인과 차감을 호출부가 한 락 안에서 한다."""

import threading

_lock = threading.Lock()
_stock: dict[str, int] = {}


def _take(sku: str, qty: int) -> bool:
    if not 1 <= qty:
        raise ValueError(qty)
    available = _stock.get(sku, 0)
    if available < qty:
        return False
    _stock[sku] = available - qty
    return True


def reserve(sku: str, qty: int) -> bool:
    return _take(sku, qty)
