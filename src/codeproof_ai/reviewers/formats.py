"""가져오기 포맷 - SARIF 만으로는 부족하다.

[실측] bandit 은 SARIF 를 지원하지 않는다 (csv·html·json·xml·yaml 뿐).
       "SARIF 를 내는 모든 도구가 리뷰어가 된다" 는 주장은 **절반만 맞다** -
       실제로는 도구마다 자기 JSON 을 내고, 포맷 어댑터가 필요하다.

그래서 포맷을 Protocol 로 둔다. 새 도구 = 파서 함수 하나.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.llm.parse import ParseOutcome, parse_findings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from codeproof_ai.domain.target import ReviewTarget


class FindingFormat(Protocol):
    """외부 도구 출력 -> Finding."""

    name: str

    def recognizes(self, payload: Any) -> bool:
        """🔴 이 포맷의 모양인가.

        파서는 모르는 모양을 받아도 예외 없이 지적 0건을 낸다 - 그러면
        **형식 착오가 「지적 0건」으로 둔갑**한다. [실측] 에이전트 출력(native)을
        기본 포맷(sarif)으로 가져오면 전 샘플이 미탐지로 채점될 뻔했다.
        """
        ...

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> ParseOutcome:
        """🔴 버린 지적은 `rejected` 에 이유를 남긴다 - 버린 것은 미탐지와 구별되지 않는다.

        [실측] SARIF · bandit 파서가 버린 것을 세지 않았다 - 경로가 다른 SARIF 를
        가져오면 exit 0 · 경고 0 · 전 샘플 「지적 0건」이었다. native 만 세고 있었다.
        """
        ...


def _has_list(payload: Any, key: str) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get(key), list)


def _quoted(target: ReviewTarget, path: str, line: int) -> str | None:
    src = target.file(path)
    if src is None:
        return None
    lines = src.content.splitlines()
    return lines[line - 1].strip() if 1 <= line <= len(lines) else None


_SARIF_LEVEL: dict[str, Severity] = {
    "none": Severity.INFO,
    "note": Severity.INFO,
    "warning": Severity.WARNING,
    "error": Severity.ERROR,
}


class SarifFormat:
    """SARIF 2.1.0. CodeQL · semgrep · Snyk · Trivy · Ruff 등.

    Args:
        categories: 도구 이름(소문자 `driver.name`) -> 룰 id -> 분류. 🔴 도구가 준 분류만 싣는다 -
            모르는 도구 · 룰은 OTHER(결함 주장)로 둔다 (F4a). [실측] 전에는 전부 OTHER 여서 Ruff 의
            관례 주장(SIM105 · style)이 직접 실행에서는 판정 불가, 가져오기에서는 FP · 탐지가 됐다.
    """

    name = "sarif"

    def __init__(self, categories: Mapping[str, Mapping[str, Category]] | None = None) -> None:
        self._categories = categories or {}

    def recognizes(self, payload: Any) -> bool:
        return _has_list(payload, "runs")

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> ParseOutcome:
        if not isinstance(payload, dict):
            return ParseOutcome(findings=(), rejected=("SARIF 가 객체가 아니다",))
        out: list[Finding] = []
        rejected: list[str] = []
        i = 0
        for run in payload.get("runs") or []:
            driver = (run.get("tool") or {}).get("driver") or {}
            rules: dict[str, Any] = {
                str(r["id"]): r
                for r in (driver.get("rules") or [])
                if isinstance(r, dict) and r.get("id") is not None
            }
            known = self._categories.get(str(driver.get("name") or "").lower(), {})
            for res in run.get("results") or []:
                got = self._one(res, rules, known, source, target)
                if isinstance(got, Finding):
                    out.append(got)
                else:
                    rejected.append(f"[{i}] {got}")
                i += 1
        return ParseOutcome(findings=tuple(out), rejected=tuple(rejected))

    def _one(
        self,
        res: Any,
        rules: dict[str, Any],
        known: Mapping[str, Category],
        source: str,
        target: ReviewTarget,
    ) -> Finding | str:
        """결과 하나를 Finding 으로. 문자열이면 버린 이유다."""
        if not isinstance(res, dict):
            return "객체가 아니다"
        locs = res.get("locations") or []
        if not locs:
            return "위치가 없다"
        phys = (locs[0] or {}).get("physicalLocation") or {}
        uri = str((phys.get("artifactLocation") or {}).get("uri", ""))
        region = phys.get("region") or {}

        src = target.match_file(uri)
        if src is None:
            return f"제시되지 않은 파일을 가리킨다: {uri!r}"
        path = src.path
        line = int(region.get("startLine", 1))
        if not target.is_visible(path, line):
            return f"범위 밖을 가리킨다: {path}:{line}"

        rule_id = str(res.get("ruleId") or "unknown")
        rule = rules.get(rule_id, {})
        return Finding(
            source=source,
            rule_id=rule_id,
            message=str((res.get("message") or {}).get("text", "")),
            # SARIF: 1-based 문자 -> 내부 규약 0-based 문자 (B1)
            location=Location(path=path, span=_sarif_span(region, line)),
            category=known.get(rule_id, Category.OTHER),
            severity=_SARIF_LEVEL.get(
                str(res.get("level", "warning")), Severity.WARNING
            ),
            quoted_code=_quoted(target, path, line),
            rule_name=str(rule.get("name") or "") or None,
            raw=dict(res),
        )


def _sarif_span(region: dict[str, Any], line: int) -> Span:
    """SARIF region 의 보고 범위.

    열은 1-based 문자이고 endColumn 은 배타적이다 - Ruff JSON 과 같은 변환이다 (B1).

    🔴 끝을 버리면 여러 줄 지적이 시작 줄로만 맞춰진다 (A2a). [실측] Ruff S112 를 직접 돌리면
       15-16 행, SARIF 로 가져오면 15 행만 남아 결함 구간과 엇갈렸다 - 같은 지적이 경로마다
       다른 자리에 있었다.
    끝이 없거나 시작보다 앞서는 깨진 region 이면 시작 줄 하나로 둔다 - 지적은 버리지 않는다 (I).
    """
    start = Position.from_char_1based(line, int(region.get("startColumn", 1)))
    end_line = int(region.get("endLine", line))
    end_column = int(region.get("endColumn", 0))
    if end_column >= 1:
        end = Position.from_char_1based(end_line, end_column)
    elif end_line > line:
        # 끝 열이 없으면 그 줄 끝까지다 - 매칭은 줄만 본다
        end = Position(line=end_line, column=0)
    else:
        return Span(start=start)
    if (end.line, end.column) < (start.line, start.column):
        return Span(start=start)
    return Span(start=start, end=end)


def _bandit_span(res: dict[str, Any], line: int) -> Span:
    """bandit 의 보고 범위. line_range 는 노드가 걸친 줄이고 col_offset · end_col_offset 은
    그 첫 줄과 끝 줄의 0-based 문자 열이다 (B1). line_number 는 대표 줄일 뿐 범위의 시작이 아니다.

    🔴 line_number 에 col_offset 을 붙이면 다른 줄의 열이 섞인다 - [실측] 한 twin 의 B602 는
       line_number 11 · line_range 9-14 · col_offset 16 (9 행 호출의 시작).
       대표 줄로만 맞추면 같은 호출을 Ruff(9 행)와 bandit(11 행)이 다른 자리에 둔다 (A2a).
    line_range 가 없는 출력이면 대표 줄 하나로 둔다.
    """
    column = int(res.get("col_offset", 0) or 0)
    lines = [n for n in res.get("line_range") or [] if isinstance(n, int) and n >= 1]
    if not lines:
        return Span(start=Position(line=line, column=column))
    start = Position(line=min(lines), column=column)
    end_column = res.get("end_col_offset")
    end = Position(
        line=max(lines),
        column=end_column if isinstance(end_column, int) and end_column >= 0 else 0,
    )
    if (end.line, end.column) < (start.line, start.column):
        return Span(start=start)
    return Span(start=start, end=end)


_BANDIT_SEVERITY: dict[str, Severity] = {
    "LOW": Severity.INFO,
    "MEDIUM": Severity.WARNING,
    "HIGH": Severity.ERROR,
}


class BanditFormat:
    """bandit `-f json`.

    [실측] bandit 은 SARIF 를 지원하지 않는다. 자기 JSON 을 낸다.
           `col_offset` 은 **0-based 문자**라 내부 규약과 이미 같다 - 다만 그 열은
           line_range 첫 줄의 열이다 (`_bandit_span`).
    """

    name = "bandit"

    def recognizes(self, payload: Any) -> bool:
        return _has_list(payload, "results")

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> ParseOutcome:
        if not isinstance(payload, dict):
            return ParseOutcome(findings=(), rejected=("bandit 출력이 객체가 아니다",))
        out: list[Finding] = []
        rejected: list[str] = []
        for i, res in enumerate(payload.get("results") or []):
            if not isinstance(res, dict):
                rejected.append(f"[{i}] 객체가 아니다")
                continue
            filename = str(res.get("filename", ""))
            src = target.match_file(filename)
            if src is None:
                rejected.append(f"[{i}] 제시되지 않은 파일을 가리킨다: {filename!r}")
                continue
            path = src.path
            line = int(res.get("line_number", 1))
            if not target.is_visible(path, line):
                rejected.append(f"[{i}] 범위 밖을 가리킨다: {path}:{line}")
                continue

            out.append(
                Finding(
                    source=source,
                    rule_id=str(res.get("test_id") or "unknown"),
                    message=str(res.get("issue_text", "")),
                    location=Location(path=path, span=_bandit_span(res, line)),
                    # bandit 은 보안 전용 스캐너다.
                    category=Category.SECURITY,
                    severity=_BANDIT_SEVERITY.get(
                        str(res.get("issue_severity", "")).upper(), Severity.WARNING
                    ),
                    quoted_code=_quoted(target, path, line),
                    rule_name=str(res.get("test_name") or "") or None,
                    raw=dict(res),
                )
            )
        return ParseOutcome(findings=tuple(out), rejected=tuple(rejected))


class NativeFormat:
    """이 플랫폼의 출력 스키마. 에이전트 출력을 손으로 맞출 때 쓴다."""

    name = "native"

    def recognizes(self, payload: Any) -> bool:
        return _has_list(payload, "findings")

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> ParseOutcome:
        if not isinstance(payload, dict):
            return ParseOutcome(findings=(), rejected=("native 출력이 객체가 아니다",))
        return parse_findings(payload, source=source, target=target)


FORMATS: dict[str, FindingFormat] = {
    f.name: f for f in (SarifFormat(), BanditFormat(), NativeFormat())
}
