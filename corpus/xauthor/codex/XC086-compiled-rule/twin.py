"""작업 식별자 검사 - 작성용 규칙을 불변 정규식 프로그램으로 컴파일한다."""

from dataclasses import dataclass
import re


@dataclass
class NameRule:
    pattern: str = r"JOB-(?P<serial>[0-9]{4})"
    flags: int = re.ASCII

    def fullmatch(self, name: str) -> re.Match[str] | None:
        return re.fullmatch(self.pattern, name, self.flags)


BOOTSTRAP = NameRule()
RULE = BOOTSTRAP


def rule() -> re.Pattern[str] | NameRule:
    return RULE


def accepts(name: str) -> bool:
    return RULE.fullmatch(name) is not None
