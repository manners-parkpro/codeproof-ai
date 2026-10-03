"""검색 색인 재구축 - 시도마다 빈 색인에서 다시 만든다."""

from collections.abc import Callable, Iterator

Load = Callable[[], Iterator[tuple[str, str]]]


def rebuild(load: Load, attempts: int = 3) -> dict[str, list[str]]:
    for attempt in range(attempts):
        index: dict[str, list[str]] = {}
        try:
            for doc_id, text in load():
                for word in sorted(set(text.split())):
                    index.setdefault(word, []).append(doc_id)
        except ConnectionError:
            if attempt == attempts - 1:
                raise
            continue
        return index
    raise ValueError("attempts 는 1 이상이어야 한다")
