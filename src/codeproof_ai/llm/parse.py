"""벤더 구조화 출력 → domain.Finding.

🔴 부분 실패를 예외로 올리지 않는다. 지적 1건이 깨져도 나머지는 살리고,
   깨진 건 세어서 남긴다 (CLAUDE.md 코드 스타일).
   한 건의 형식 오류로 실행 전체를 버리면 표본이 줄고 비용만 나간다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span

if TYPE_CHECKING:
    from codeproof_ai.domain.target import ReviewTarget


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """파싱 결과와 버려진 것들."""

    findings: tuple[Finding, ...]
    rejected: tuple[str, ...] = field(default_factory=tuple)
    """버려진 이유들. 매니페스트에 남겨 표본 손실을 추적한다."""


def _as_int(value: object, default: int = 1) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return default


def parse_body(text: str, *, source: str, target: ReviewTarget) -> ParseOutcome:
    """모델 본문(JSON 문자열) → Finding. 읽지 못한 본문은 버린 이유로 센다 (I).

    🔴 세 어댑터가 따로 읽을 때는 JSON 이 아니거나 객체가 아닌 본문이 버린 이유 없이 「지적 0건」이
       됐다 - `review --ollama` 화면에는 0건만 남았다. 빈 본문은 `findings` 가 없는 것으로 센다.
    """
    try:
        loaded = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        return ParseOutcome(findings=(), rejected=("본문이 JSON 이 아니다",))
    if not isinstance(loaded, dict):
        why = f"본문이 객체가 아니다 ({type(loaded).__name__})"
        return ParseOutcome(findings=(), rejected=(why,))
    return parse_findings(loaded, source=source, target=target)


def parse_findings(
    payload: dict[str, Any], *, source: str, target: ReviewTarget
) -> ParseOutcome:
    """구조화 출력에서 Finding 들을 만든다.

    제약 디코딩이 스키마를 보장하지만, 값의 **의미**까지 보장하지는 않는다.
    모델은 제시되지 않은 파일이나 범위 밖 줄을 가리킬 수 있다.
    그건 스키마 위반이 아니라 **환각**이고, 여기서 걸러 기록한다.
    """
    raw = payload.get("findings")
    if not isinstance(raw, list):
        return ParseOutcome(findings=(), rejected=("findings 가 배열이 아니다",))

    out: list[Finding] = []
    rejected: list[str] = []

    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            rejected.append(f"[{i}] 객체가 아니다")
            continue

        path = str(item.get("file", ""))
        start = _as_int(item.get("line_start"))
        end = _as_int(item.get("line_end"), start)

        if target.file(path) is None:
            rejected.append(f"[{i}] 제시되지 않은 파일을 가리킨다: {path!r}")
            continue
        if not target.is_visible(path, start):
            rejected.append(f"[{i}] 범위 밖을 가리킨다: {path}:{start}")
            continue
        end = max(end, start)

        try:
            category = Category(str(item.get("category", "other")))
        except ValueError:
            category = Category.OTHER
        try:
            severity = Severity(str(item.get("severity", "warning")))
        except ValueError:
            severity = Severity.WARNING

        out.append(
            Finding(
                source=source,
                rule_id=category.value,
                message=str(item.get("message", "")),
                location=Location(
                    path=path,
                    span=Span(
                        start=Position(line=start, column=0),
                        end=Position(line=end, column=0),
                    ),
                ),
                category=category,
                severity=severity,
                quoted_code=str(item.get("quoted_code", "")) or None,
                hint=str(item.get("failure_mode", "")) or None,
                raw=dict(item),
            )
        )

    return ParseOutcome(findings=tuple(out), rejected=tuple(rejected))
