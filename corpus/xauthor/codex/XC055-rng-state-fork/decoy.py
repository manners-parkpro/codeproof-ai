"""무작위 배치 미리보기 - 난수 생성기의 전체 상태를 새 인스턴스에 복원한다."""

from random import Random


def fork_rng(source: Random) -> Random:
    working = Random(0)
    working.setstate(source.getstate())
    return working


def preview_shuffle(
    source: Random, entries: tuple[str, ...]
) -> tuple[list[str], Random]:
    working = fork_rng(source)
    arranged = list(entries)
    working.shuffle(arranged)
    return arranged, working
