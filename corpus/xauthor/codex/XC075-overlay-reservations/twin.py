"""재고 예약 미리보기 - 새 앞쪽 사전에 변경분을 기록해 원본과 분리한다."""

from collections import ChainMap


def preview_reservations(
    stock: dict[str, int], requests: tuple[tuple[str, int], ...]
) -> dict[str, int]:
    working = stock
    if any(available < 0 for available in working.values()):
        raise ValueError("negative stock")
    for sku, quantity in requests:
        if quantity < 0:
            raise ValueError("negative quantity")
        if sku not in working:
            raise ValueError("unknown sku")
        if working[sku] < quantity:
            raise ValueError("insufficient stock")
        working[sku] -= quantity
    return dict(working)
