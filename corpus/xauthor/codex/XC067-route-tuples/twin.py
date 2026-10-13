"""부하별 작업 큐 선택 - 초기 설정의 각 행과 표를 튜플로 고정한다."""

BOOTSTRAP = [[0, 3], [50, 2], [80, 1]]
ROUTES = tuple(BOOTSTRAP)


def routing_table():
    return ROUTES


def route(load: int) -> int:
    for threshold, queue in reversed(ROUTES):
        if load >= threshold:
            return queue
    return 3
