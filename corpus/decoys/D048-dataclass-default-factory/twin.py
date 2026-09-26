"""작업 항목 - 기본값이 인스턴스마다 새로 만들어진다."""

from dataclasses import dataclass, field

_SHARED: list[str] = []


@dataclass
class Job:
    name: str
    tags: list[str] = field(default_factory=lambda: _SHARED)

    def tag(self, value: str) -> None:
        self.tags.append(value)
