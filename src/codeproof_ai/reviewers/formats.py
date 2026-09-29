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
from codeproof_ai.llm.parse import parse_findings

if TYPE_CHECKING:
    from codeproof_ai.domain.target import ReviewTarget


class FindingFormat(Protocol):
    """외부 도구 출력 -> Finding."""

    name: str

    def recognizes(self, payload: Any) -> bool:
        """🔴 이 포맷의 모양인가.

        파서는 모르는 모양을 받아도 예외 없이 빈 튜플을 낸다 - 그러면
        **형식 착오가 「지적 0건」으로 둔갑**한다. [실측] 에이전트 출력(native)을
        기본 포맷(sarif)으로 가져오면 전 샘플이 미탐지로 채점될 뻔했다.
        """
        ...

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> tuple[Finding, ...]:
        ...


def _has_list(payload: Any, key: str) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get(key), list)


def _match_path(uri: str, target: ReviewTarget) -> str | None:
    for p in target.visible_paths:
        if uri.endswith(p):
            return p
    return None


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
    """SARIF 2.1.0. CodeQL · semgrep · Snyk · Trivy · Ruff 등."""

    name = "sarif"

    def recognizes(self, payload: Any) -> bool:
        return _has_list(payload, "runs")

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> tuple[Finding, ...]:
        if not isinstance(payload, dict):
            return ()
        out: list[Finding] = []
        for run in payload.get("runs") or []:
            driver = (run.get("tool") or {}).get("driver") or {}
            rules: dict[str, Any] = {
                str(r["id"]): r
                for r in (driver.get("rules") or [])
                if isinstance(r, dict) and r.get("id") is not None
            }
            for res in run.get("results") or []:
                f = self._one(res, rules, source, target)
                if f is not None:
                    out.append(f)
        return tuple(out)

    def _one(
        self, res: Any, rules: dict[str, Any], source: str, target: ReviewTarget
    ) -> Finding | None:
        if not isinstance(res, dict):
            return None
        locs = res.get("locations") or []
        if not locs:
            return None
        phys = (locs[0] or {}).get("physicalLocation") or {}
        uri = str((phys.get("artifactLocation") or {}).get("uri", ""))
        region = phys.get("region") or {}

        path = _match_path(uri, target)
        if path is None:
            return None
        line = int(region.get("startLine", 1))
        if not target.is_visible(path, line):
            return None

        rule_id = str(res.get("ruleId") or "unknown")
        rule = rules.get(rule_id, {})
        return Finding(
            source=source,
            rule_id=rule_id,
            message=str((res.get("message") or {}).get("text", "")),
            # SARIF: 1-based 문자 -> 내부 규약 0-based 문자 (B1)
            location=Location(
                path=path,
                span=Span(
                    start=Position.from_char_1based(
                        line, int(region.get("startColumn", 1))
                    )
                ),
            ),
            category=Category.OTHER,
            severity=_SARIF_LEVEL.get(
                str(res.get("level", "warning")), Severity.WARNING
            ),
            quoted_code=_quoted(target, path, line),
            rule_name=str(rule.get("name") or "") or None,
            raw=dict(res),
        )


_BANDIT_SEVERITY: dict[str, Severity] = {
    "LOW": Severity.INFO,
    "MEDIUM": Severity.WARNING,
    "HIGH": Severity.ERROR,
}


class BanditFormat:
    """bandit `-f json`.

    [실측] bandit 은 SARIF 를 지원하지 않는다. 자기 JSON 을 낸다.
           `col_offset` 은 **0-based 문자**라 내부 규약과 이미 같다.
    """

    name = "bandit"

    def recognizes(self, payload: Any) -> bool:
        return _has_list(payload, "results")

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> tuple[Finding, ...]:
        if not isinstance(payload, dict):
            return ()
        out: list[Finding] = []
        for res in payload.get("results") or []:
            if not isinstance(res, dict):
                continue
            path = _match_path(str(res.get("filename", "")), target)
            if path is None:
                continue
            line = int(res.get("line_number", 1))
            if not target.is_visible(path, line):
                continue

            out.append(
                Finding(
                    source=source,
                    rule_id=str(res.get("test_id") or "unknown"),
                    message=str(res.get("issue_text", "")),
                    location=Location(
                        path=path,
                        span=Span(
                            start=Position(
                                line=line, column=int(res.get("col_offset", 0) or 0)
                            )
                        ),
                    ),
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
        return tuple(out)


class NativeFormat:
    """이 플랫폼의 출력 스키마. 에이전트 출력을 손으로 맞출 때 쓴다."""

    name = "native"

    def recognizes(self, payload: Any) -> bool:
        return _has_list(payload, "findings")

    def parse(
        self, payload: Any, source: str, target: ReviewTarget
    ) -> tuple[Finding, ...]:
        if not isinstance(payload, dict):
            return ()
        return parse_findings(payload, source=source, target=target).findings


FORMATS: dict[str, FindingFormat] = {
    f.name: f for f in (SarifFormat(), BanditFormat(), NativeFormat())
}
