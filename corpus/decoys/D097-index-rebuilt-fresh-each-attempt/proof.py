"""D097 반증 - 읽는 도중에 연결이 끊기는 원본으로 재시도를 일으킨다."""

from __future__ import annotations

from collections.abc import Iterator
from types import ModuleType

_DOCS = [("d1", "red apple"), ("d2", "green apple pie"), ("d3", "red red pie"), ("d4", "plum")]


def _expected() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for doc_id, text in _DOCS:
        for word in sorted(set(text.split())):
            index.setdefault(word, []).append(doc_id)
    return index


class _Flaky:
    """처음 몇 번의 읽기는 정해 둔 문서 수만큼 내준 뒤 끊긴다."""

    def __init__(self, cuts: list[int], error: type[ConnectionError] = ConnectionError) -> None:
        self._cuts = list(cuts)
        self._error = error

    def __call__(self) -> Iterator[tuple[str, str]]:
        cut = self._cuts.pop(0) if self._cuts else None
        for n, doc in enumerate(_DOCS):
            if n == cut:
                raise self._error("읽는 도중 끊김")
            yield doc


def attack(mod: ModuleType) -> bool:
    """재시도 뒤 돌려받은 색인이 끝까지 한 번 읽은 결과와 다른가.

    끊기는 자리(첫 문서 전 · 중간 · 마지막 문서 전)와 끊김 횟수(1 · 2)를 바꿔 가며 친다 - 실패한 시도의
    조각이 남으면 중복이, 실패한 시도의 결과를 돌려주면 누락이 드러난다 (DESIGN §3.5 「재시도 · 멱등」).

    decoy 는 시도마다 index 를 새로 만든다. twin 은 한 번만 만들어 끊긴 시도의 번호가 남는다.
    """
    want = _expected()
    for cuts in ([0], [1], [2], [3], [2, 1], [3, 3]):
        for error in (ConnectionError, ConnectionResetError):
            if mod.rebuild(_Flaky(cuts, error)) != want:
                return True
    # 🔴 끊긴 뒤 원본이 바뀌어도 마지막에 끝까지 읽은 판만 남는다 - 시도마다 같은 문서만 내면 재설정 대신
    #    중복만 막는 약화 · 목록만 비우는 약화가 지나간다 (독립 검토)
    first = [("d1", "red apple"), ("d2", "green apple pie")]
    second = [("d1", "red apple"), ("d2", "green pear")]
    reads = iter([first, second])

    def changing() -> Iterator[tuple[str, str]]:
        docs = next(reads)
        yield from docs
        if docs is first:
            raise ConnectionError("읽는 도중 끊김")

    want = {"apple": ["d1"], "red": ["d1"], "green": ["d2"], "pear": ["d2"]}
    if mod.rebuild(changing) != want:
        return True
    # 시도를 다 써도 끊기면 마지막 예외가 올라가고 조각을 돌려주지 않는다
    try:
        mod.rebuild(_Flaky([1, 1, 1]))
    except Exception:  # noqa: BLE001 - 어떤 예외로 끝나든 조각을 돌려주지 않으면 된다
        return False
    return True
