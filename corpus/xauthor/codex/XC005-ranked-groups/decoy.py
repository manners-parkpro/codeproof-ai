"""그룹별 상위 점수 추출 - 바깥 목록과 각 점수 목록을 복사한다."""


def _copy_groups(groups: list[list[int]]) -> list[list[int]]:
    return [list(group) for group in groups]


def _rank_in_place(groups: list[list[int]], count: int) -> None:
    for group in groups:
        group.sort(reverse=True)
        del group[count:]
    groups[:] = [group for group in groups if group]


def top_scores(groups: list[list[int]], count: int) -> list[list[int]]:
    if count < 0:
        raise ValueError("count must be nonnegative")
    groups = _copy_groups(groups)
    _rank_in_place(groups, count)
    return groups
