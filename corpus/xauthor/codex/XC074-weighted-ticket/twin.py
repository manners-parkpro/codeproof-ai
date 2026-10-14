"""가중 티켓의 소속 버킷 조회 - 누적 가중치의 반열린 구간으로 경계를 배정한다."""


def bucket_for_ticket(weights: list[int], ticket: int) -> int:
    """음수 가중치나 범위 밖 티켓은 거절하고, 누적합 구간 [앞 합, 현재 합)의 인덱스를 반환한다."""
    if any(weight < 0 for weight in weights):
        raise ValueError("negative weight")
    if ticket < 0 or ticket >= sum(weights):
        raise ValueError("ticket out of range")
    remaining = ticket
    for index, weight in enumerate(weights):
        if remaining > weight:
            remaining -= weight
            continue
        return index
    raise RuntimeError("unassigned ticket")
