"""이벤트 스트림 미리보기 - 수집기에 넘기기 전에 지연 이터레이터로 항목 수를 제한한다."""

from collections.abc import Iterable, Sequence
from itertools import islice


def preview(records: Iterable[str]) -> Sequence[str]:
    return _materialize(islice(records, 64))


def _materialize(records: Iterable[str]) -> Sequence[str]:
    return list(records)
