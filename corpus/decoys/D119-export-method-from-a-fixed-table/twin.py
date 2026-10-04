"""보고서 내보내기 - 부르는 형식 메서드 이름은 공개 함수의 고정 표에서만 온다."""

from typing import Protocol


class Exporter(Protocol):
    def to_csv(self, rows: list[dict[str, str]]) -> str: ...
    def to_json(self, rows: list[dict[str, str]]) -> str: ...


_METHODS = {"csv": "to_csv", "json": "to_json"}


def _render(exporter: Exporter, method: str, rows: list[dict[str, str]]) -> str:
    return getattr(exporter, method)(rows)


def export(exporter: Exporter, fmt: str, rows: list[dict[str, str]]) -> str:
    method = _METHODS.get(fmt, fmt)
    return _render(exporter, method, rows)
