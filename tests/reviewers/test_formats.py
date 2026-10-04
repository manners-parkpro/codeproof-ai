"""가져오기 포맷 파서.

🔴 여기가 컬럼 규약(B1)의 경계다. SARIF 는 1-based 문자, bandit 은
   0-based 문자 - 둘을 같은 코드로 다루면 조용히 한 칸씩 틀린다.

[실측] bandit 은 SARIF 를 지원하지 않는다 (csv·html·json·xml·yaml 뿐).
       「SARIF 를 내는 모든 도구가 리뷰어가 된다」는 절반만 맞았고,
       그래서 포맷이 Protocol 이 됐다.
"""

from __future__ import annotations

from typing import Any

import pytest

from codeproof_ai.domain.finding import Category, Severity
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.reviewers.formats import (
    FORMATS,
    BanditFormat,
    NativeFormat,
    SarifFormat,
)

SRC = 'import subprocess\nx = 1\nrun(cmd, shell=True)\n'
TARGET = ReviewTarget(target_id="t", files=(SourceFile("m.py", SRC),))


def _first_result(payload: Any) -> Any:
    return payload["runs"][0]["results"][0]


def _sarif(uri: str = "m.py", line: int = 3, col: int = 5) -> Any:
    return {
        "runs": [
            {
                "tool": {"driver": {"name": "x", "rules": [
                    {"id": "S602", "name": "shell-true"}
                ]}},
                "results": [
                    {
                        "ruleId": "S602",
                        "level": "error",
                        "message": {"text": "shell=True"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": uri},
                                    "region": {"startLine": line, "startColumn": col},
                                }
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _bandit(filename: str = "/tmp/x/m.py", line: int = 3, col: int = 4) -> Any:
    return {
        "results": [
            {
                "test_id": "B602",
                "test_name": "subprocess_popen_with_shell_equals_true",
                "issue_text": "subprocess call with shell=True",
                "issue_severity": "HIGH",
                "filename": filename,
                "line_number": line,
                "col_offset": col,
            }
        ]
    }


class TestRegistry:
    def test_all_three_formats_registered(self) -> None:
        assert set(FORMATS) == {"sarif", "bandit", "native"}

    def test_names_match_keys(self) -> None:
        for key, fmt in FORMATS.items():
            assert fmt.name == key


class TestSarifColumns:
    """🔴 SARIF 는 **1-based 문자** - 내부 규약은 0-based."""

    def test_column_is_converted(self) -> None:
        f = SarifFormat().parse(_sarif(col=5), "x", TARGET).findings[0]
        assert f.location.span.start.column == 4, "1-based 를 그대로 썼다"

    def test_line_is_unchanged(self) -> None:
        f = SarifFormat().parse(_sarif(line=3), "x", TARGET).findings[0]
        assert f.location.span.start.line == 3

    def test_rule_name_comes_from_rules_table(self) -> None:
        f = SarifFormat().parse(_sarif(), "x", TARGET).findings[0]
        assert f.rule_name == "shell-true"

    def test_severity_is_normalized(self) -> None:
        f = SarifFormat().parse(_sarif(), "x", TARGET).findings[0]
        assert f.severity is Severity.ERROR

    def test_quoted_code_is_filled_from_source(self) -> None:
        f = SarifFormat().parse(_sarif(line=3), "x", TARGET).findings[0]
        assert f.quoted_code == "run(cmd, shell=True)"


class TestSarifCategories:
    """🔴 분류는 그 SARIF 를 낸 도구에 묻는다 - 모르는 도구 · 룰은 OTHER(결함 주장)다 (F4a).

    [실측] 전에는 전부 OTHER 여서 Ruff 의 관례 주장(SIM105 · style)이 직접 실행에서는
    판정 불가, 가져오기에서는 FP · 탐지로 채점됐다.
    """

    @staticmethod
    def _from(tool: str) -> Any:
        payload = _sarif()
        payload["runs"][0]["tool"]["driver"]["name"] = tool
        return payload

    def test_the_tools_own_category_is_used(self) -> None:
        fmt = SarifFormat({"ruff": {"S602": Category.STYLE}})
        assert fmt.parse(self._from("ruff"), "x", TARGET).findings[0].category is Category.STYLE

    def test_another_tool_with_the_same_rule_id_stays_a_defect_claim(self) -> None:
        """룰 id 가 같아도 다른 도구가 냈으면 그 분류를 빌려 오지 않는다."""
        fmt = SarifFormat({"ruff": {"S602": Category.STYLE}})
        assert fmt.parse(self._from("semgrep"), "x", TARGET).findings[0].category is Category.OTHER

    def test_without_a_catalog_everything_is_a_defect_claim(self) -> None:
        found = SarifFormat().parse(self._from("ruff"), "x", TARGET).findings[0]
        assert found.category is Category.OTHER


class TestSarifReportedRange:
    """🔴 SARIF 지적도 보고 범위의 끝까지 싣는다.

    시작 줄만 남으면 직접 실행과 다른 자리가 된다 (A2a).
    """

    @staticmethod
    def _with_end(**end: int) -> Any:
        payload = _sarif(line=2, col=1)
        _first_result(payload)["locations"][0]["physicalLocation"]["region"].update(end)
        return payload

    def test_end_of_region_is_kept(self) -> None:
        payload = self._with_end(endLine=3, endColumn=21)
        f = SarifFormat().parse(payload, "x", TARGET).findings[0]
        end = f.location.span.end
        assert end is not None
        assert (end.line, end.column) == (3, 20)
        assert f.location.span.overlaps(3, 3), "끝 줄만 겹치는 결함 구간도 같은 자리다"

    def test_end_line_without_end_column_still_spans_lines(self) -> None:
        f = SarifFormat().parse(self._with_end(endLine=3), "x", TARGET).findings[0]
        assert f.location.span.overlaps(3, 3)

    def test_region_without_end_is_one_line(self) -> None:
        f = SarifFormat().parse(_sarif(line=3, col=5), "x", TARGET).findings[0]
        assert f.location.span.end is None

    def test_end_before_start_keeps_the_finding(self) -> None:
        """깨진 region 이어도 지적은 살린다 - 끝만 모른다고 둔다 (I)."""
        out = SarifFormat().parse(self._with_end(endLine=1, endColumn=1), "x", TARGET)
        assert len(out.findings) == 1
        assert out.findings[0].location.span.end is None


class TestBanditColumns:
    """🔴 bandit 의 col_offset 은 **이미 0-based 문자** - 변환하면 안 된다."""

    def test_column_is_not_shifted(self) -> None:
        f = BanditFormat().parse(_bandit(col=4), "x", TARGET).findings[0]
        assert f.location.span.start.column == 4, "0-based 를 또 변환했다"

    def test_reported_range_is_the_span(self) -> None:
        """🔴 범위는 line_range 다 - line_number 는 대표 줄이다 (A2a)."""
        payload = _bandit(line=3, col=0)
        payload["results"][0].update(line_range=[2, 3], end_col_offset=20)
        span = BanditFormat().parse(payload, "x", TARGET).findings[0].location.span
        assert (span.start.line, span.start.column) == (2, 0)
        assert span.end is not None
        assert (span.end.line, span.end.column) == (3, 20)

    def test_column_belongs_to_the_first_line_of_the_range(self) -> None:
        """🔴 col_offset 은 line_range 첫 줄의 열이다 - 대표 줄에 붙이면 다른 줄의 열이 섞인다 (B1).
        """
        payload = _bandit(line=3, col=4)
        payload["results"][0]["line_range"] = [1, 2, 3]
        span = BanditFormat().parse(payload, "x", TARGET).findings[0].location.span
        assert (span.start.line, span.start.column) == (1, 4)

    def test_without_line_range_the_representative_line_is_used(self) -> None:
        span = BanditFormat().parse(_bandit(line=3, col=4), "x", TARGET).findings[0].location.span
        assert (span.start.line, span.start.column, span.end) == (3, 4, None)

    def test_category_is_security(self) -> None:
        """bandit 은 보안 전용 스캐너다."""
        f = BanditFormat().parse(_bandit(), "x", TARGET).findings[0]
        assert f.category is Category.SECURITY

    def test_severity_mapping(self) -> None:
        for level, expected in (
            ("LOW", Severity.INFO),
            ("MEDIUM", Severity.WARNING),
            ("HIGH", Severity.ERROR),
        ):
            payload = _bandit()
            payload["results"][0]["issue_severity"] = level
            f = BanditFormat().parse(payload, "x", TARGET).findings[0]
            assert f.severity is expected, level

    def test_absolute_path_is_matched_by_suffix(self) -> None:
        """임시 디렉터리 절대경로가 대상 상대경로로 되돌아와야 한다."""
        f = BanditFormat().parse(_bandit(filename="/a/b/c/m.py"), "x", TARGET).findings[0]
        assert f.location.path == "m.py"


class TestOutOfScopeFindingsAreCounted:
    """🔴 제시되지 않은 파일·범위를 가리키는 지적은 버리되 **센다**.

    버린 것은 미탐지와 구별되지 않는다. [실측] SARIF · bandit 은 버린 것을 세지 않았다 -
    경로가 다른 SARIF 가 지적 0 · 경고 0 으로 들어왔다.
    """

    @pytest.mark.parametrize(
        ("fmt", "payload"),
        [
            (SarifFormat(), _sarif(uri="ghost.py")),
            (BanditFormat(), _bandit(filename="/x/ghost.py")),
        ],
        ids=["sarif", "bandit"],
    )
    def test_unknown_file(self, fmt: Any, payload: Any) -> None:
        out = fmt.parse(payload, "x", TARGET)
        assert out.findings == ()
        assert len(out.rejected) == 1
        assert "ghost.py" in out.rejected[0]

    @pytest.mark.parametrize(
        ("fmt", "payload"),
        [
            (SarifFormat(), _sarif(line=999)),
            (BanditFormat(), _bandit(line=999)),
        ],
        ids=["sarif", "bandit"],
    )
    def test_line_out_of_range(self, fmt: Any, payload: Any) -> None:
        out = fmt.parse(payload, "x", TARGET)
        assert out.findings == ()
        assert len(out.rejected) == 1
        assert "범위 밖" in out.rejected[0]

    @pytest.mark.parametrize(
        ("fmt", "payload"),
        [(SarifFormat(), _sarif()), (BanditFormat(), _bandit())],
        ids=["sarif", "bandit"],
    )
    def test_in_scope_finding_is_not_counted(self, fmt: Any, payload: Any) -> None:
        """대조군 - 같은 경로에서 제시된 파일을 가리키면 지적이 나오고 버림은 0건이다."""
        out = fmt.parse(payload, "x", TARGET)
        assert len(out.findings) == 1
        assert out.rejected == ()


class TestMalformedInputDoesNotRaise:
    """🔴 깨진 입력으로 실행을 멈추지 않는다 - 대신 버린 이유를 남긴다."""

    @pytest.mark.parametrize("fmt", list(FORMATS.values()), ids=list(FORMATS))
    def test_non_dict(self, fmt: Any) -> None:
        payloads: tuple[Any, ...] = ([], "nope")
        for payload in payloads:
            out = fmt.parse(payload, "x", TARGET)
            assert out.findings == ()
            assert len(out.rejected) == 1

    def test_sarif_without_locations(self) -> None:
        payload = _sarif()
        _first_result(payload)["locations"] = []
        out = SarifFormat().parse(payload, "x", TARGET)
        assert out.findings == ()
        assert out.rejected == ("[0] 위치가 없다",)

    def test_sarif_with_rule_missing_id(self) -> None:
        """id 없는 룰 항목이 있어도 결과 파싱이 죽지 않는다."""
        payload = _sarif()
        payload["runs"][0]["tool"]["driver"]["rules"] = [{"name": "x"}]
        assert len(SarifFormat().parse(payload, "x", TARGET).findings) == 1

    def test_bandit_with_non_dict_result(self) -> None:
        out = BanditFormat().parse({"results": ["nope"]}, "x", TARGET)
        assert out.findings == ()
        assert out.rejected == ("[0] 객체가 아니다",)


class TestNativeFormat:
    def test_parses_platform_schema(self) -> None:
        payload = {
            "findings": [
                {
                    "file": "m.py",
                    "line_start": 3,
                    "line_end": 3,
                    "category": "security",
                    "severity": "error",
                    "quoted_code": "run(cmd, shell=True)",
                    "message": "m",
                    "failure_mode": "f",
                }
            ]
        }
        out = NativeFormat().parse(payload, "agent", TARGET).findings
        assert len(out) == 1
        assert out[0].source == "agent"
        assert out[0].hint == "f"
