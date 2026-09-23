"""안전 근거의 **구조적** 확인 - 실행 반증을 보완한다.

🔴 이 파일은 더 이상 1차 방어선이 아니다.

   1차는 쌍마다 있는 `proof.py` 이고 `tests/corpus/test_proofs.py` 가
   **예외 없이 전수로** 강제한다. 여기에는 실행보다 정적 추론이 강한 경우만
   남긴다 - 대표적으로 「외부 입력이 이 sink 에 닿는 경로가 **없다**」 처럼
   **부재를 증명**하는 주장이다. 실행은 부재를 보일 수 없고 AST 는 보일 수 있다.

## 왜 역할을 나눴는가

전에는 이 파일이 유일한 실행 검증이었고, 못 쓰겠는 것은 `UNTESTED_BY_DESIGN`
면제 목록에 적었다. 그 결과 19쌍 중 **8쌍(42%)에 twin 반증이 없었다.**
그리고 면제 사유 다섯 개가 전부 틀린 것으로 드러났다:

| 면제 사유 | 실제 |
|---|---|
| 동시성은 단위 테스트로 재현 불가 (D003·D015) | `race_window` 로 재현된다 |
| 자원 수명은 부수효과 확인이 무겁다 (D004·D014) | `Path.open` 가로채기 · 합 보존으로 충분 |
| 경로 탈출은 실제 파일시스템이 필요 (D008) | 반환 경로만 보면 된다 |
| D018 이 같은 계약을 덮는다 (D005) | 다른 코드 · 다른 주장이다 |
| D017 이 같은 성질을 덮는다 (D009) | 같다 |

「너무 어렵다」가 조용히 「검증 안 됨」이 되는 자리였다.
**그래서 면제 기구를 없앴다** - 공격을 못 쓰면 그 decoy 는 싣지 않는다.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _load(decoy_id: str, side: str = "decoy") -> ModuleType:
    """decoy 의 한쪽을 모듈로 읽는다. 대상마다 이름을 달리해 충돌을 피한다."""
    path = DECOYS / decoy_id / f"{side}.py"
    name = f"_decoy_{decoy_id.replace('-', '_')}_{side}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestUpstreamValidation:
    """D001 · D011 — 상류 검증이 아래 접근을 보장하는가."""

    def test_d001_missing_key_is_rejected_before_access(self) -> None:
        m = _load("D001-upstream-validated-dict-access")
        with pytest.raises(m.ConfigError):
            m.load({"host": "h"})  # port·timeout 누락
        assert m.load({"host": "h", "port": "1", "timeout": "2"}).port == 1

    def test_d001_twin_actually_breaks(self) -> None:
        """🔴 twin 이 진짜 결함이어야 짝이 성립한다."""
        t = _load("D001-upstream-validated-dict-access", "twin")
        with pytest.raises(KeyError):
            t.load({"host": "h"})

    def test_d011_only_allowlisted_attributes_reachable(self) -> None:
        m = _load("D011-validated-attr-access")
        snap = m.Snapshot()
        assert m.read(snap, "latency") == 0.0
        for evil in ("__class__", "__dict__", "nope"):
            with pytest.raises(KeyError):
                m.read(snap, evil)

    def test_d011_twin_reaches_dunder(self) -> None:
        t = _load("D011-validated-attr-access", "twin")
        with pytest.raises((TypeError, AttributeError)):
            t.read(t.Snapshot(), "__class__")


class TestTypeNarrowing:
    """D006 · D012 — 좁힘이 실제로 접근을 보장하는가."""

    def test_d006_empty_input_returns_early(self) -> None:
        m = _load("D006-emptiness-narrowed")
        assert m.total([]) == 0
        assert m.total([m.Row(3), m.Row(4)]) == 7

    def test_d006_twin_raises_on_empty(self) -> None:
        t = _load("D006-emptiness-narrowed", "twin")
        with pytest.raises(IndexError):
            t.total([])

    def test_d012_binary_event_never_reaches_body(self) -> None:
        m = _load("D012-isinstance-narrowed")
        assert m.summarize(m.BinaryEvent(b"abc")).startswith("<binary")
        assert m.summarize(m.TextEvent("  Hi ")) == "hi"

    def test_d012_twin_raises_on_binary(self) -> None:
        t = _load("D012-isinstance-narrowed", "twin")
        with pytest.raises(AttributeError):
            t.summarize(t.BinaryEvent(b"abc"))


class TestConstantOnlySink:
    """D002 · D013 — 외부 입력이 위험 API 에 닿지 않는가."""

    def test_d013_takes_no_argument(self) -> None:
        """인자가 없으면 호출자가 표현식에 영향을 줄 수단이 없다."""
        m = _load("D013-eval-on-literal")
        assert list(inspect.signature(m.threshold_seconds).parameters) == []
        assert m.threshold_seconds() == 86400

    def test_d002_command_is_a_module_constant(self) -> None:
        """🔴 subprocess 를 실행하지 않고 **정적으로** 확인한다.

        근거는 「외부 입력이 커맨드에 닿는 경로가 없다」이므로,
        AST 로 그 경로의 부재를 보이는 것이 실행보다 정확하다.
        """
        src = (DECOYS / "D002-shell-true-constant-command" / "decoy.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(src)

        fn = next(
            n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "is_healthy"
        )
        assert not fn.args.args, "인자가 있으면 외부 입력 경로가 생긴다"

        call = next(
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "run"
        )
        cmd = call.args[0]
        assert isinstance(cmd, ast.Name), f"커맨드가 이름 참조가 아니다: {ast.dump(cmd)}"
        assert cmd.id == "_HEALTHCHECK_CMD"

        assigned = next(
            n for n in tree.body
            if isinstance(n, ast.Assign)
            and any(getattr(t, "id", None) == "_HEALTHCHECK_CMD" for t in n.targets)
        )
        assert isinstance(assigned.value, ast.Constant), (
            "커맨드 상수가 리터럴이 아니다 - 포매팅·연결이 있으면 근거가 깨진다"
        )

    def test_d002_twin_interpolates_an_argument(self) -> None:
        src = (DECOYS / "D002-shell-true-constant-command" / "twin.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(src)
        fn = next(
            n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "is_healthy"
        )
        assert [a.arg for a in fn.args.args] == ["service"], (
            "twin 이 외부 입력을 받아야 짝이 성립한다"
        )
        assert any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "format"
            for n in ast.walk(fn)
        ), "twin 이 커맨드를 조립해야 한다"

    def test_d013_twin_accepts_external_expression(self) -> None:
        t = _load("D013-eval-on-literal", "twin")
        assert list(inspect.signature(t.threshold_seconds).parameters) == ["user_expr"]
        assert t.threshold_seconds("2*3") == 6  # 외부 표현식이 실행된다


class TestMisleadingName:
    """D007 · D016 — 이름이 위험하지만 값은 검증됐는가."""

    def test_d007_rejects_markup(self) -> None:
        m = _load("D007-misleading-unsafe-name")
        assert "<span" in m.render("ok_name")
        with pytest.raises(ValueError, match="rejected"):
            m.render("<script>")

    def test_d016_date_interpolation_has_no_sql_metacharacters(self) -> None:
        """🔴 date 값 자체에 따옴표·세미콜론이 없어야 근거가 성립한다."""
        m = _load("D016-raw-prefix-already-parsed")
        q = m.build_query("2024-01-01~2024-06-30")
        rendered = str(date(2024, 1, 1))
        assert not set(rendered) & set("';\"-\\") - {"-"}, rendered
        assert q.count("'") == 4, f"따옴표가 4개여야 한다: {q}"

    def test_d016_malformed_input_is_rejected(self) -> None:
        m = _load("D016-raw-prefix-already-parsed")
        for evil in ("2024-01-01' OR '1'='1~2024-06-30", "nope~nope"):
            with pytest.raises(ValueError):
                m.build_query(evil)

    def test_d016_twin_admits_injection(self) -> None:
        t = _load("D016-raw-prefix-already-parsed", "twin")
        q = t.build_query("2024-01-01' OR '1'='1~x")
        assert "OR" in q, "twin 이 주입을 허용해야 짝이 성립한다"


class TestNoopShimNeighbor:
    """D008 · D019 — 진짜 검증 함수가 불리는가."""

    def test_d019_control_characters_are_stripped(self) -> None:
        m = _load("D019-noop-escape-neighbor")
        sink: list[str] = []
        m.write("ok\n[audit] FORGED\x00\x1b", sink)
        assert len("".join(sink).splitlines()) == 1, "로그 줄을 위조할 수 있다"

    def test_d019_twin_allows_forgery(self) -> None:
        t = _load("D019-noop-escape-neighbor", "twin")
        sink: list[str] = []
        t.write("ok\n[audit] FORGED", sink)
        assert len("".join(sink).splitlines()) == 2


class TestUnreachableBranch:
    """D009 · D017 — 앞선 분기가 정말 전체를 덮는가."""

    def test_d017_active_states_are_fully_covered(self) -> None:
        m = _load("D017-validated-before-dispatch")
        assert {m.next_state(s) for s in m._ACTIVE} == {"running", "done"}
        with pytest.raises(ValueError, match="done"):
            m.next_state("done")

    def test_d017_twin_hits_the_dead_branch(self) -> None:
        t = _load("D017-validated-before-dispatch", "twin")
        with pytest.raises(AttributeError):
            t.next_state("anything-else")


class TestHalfOpenContract:
    """D005 · D018 — 반열린 구간 계약이 일관되는가."""

    def test_d018_size_matches_contains(self) -> None:
        m = _load("D018-exclusive-upper-bound")
        r = m.Range(1, 4)
        counted = sum(1 for v in range(0, 10) if m.contains(r, v))
        assert counted == m.size(r) == 3, "size 와 contains 가 어긋난다"
        assert not m.contains(r, 4), "배타적 상한인데 포함됐다"

    def test_d018_rejects_degenerate_ranges(self) -> None:
        m = _load("D018-exclusive-upper-bound")
        for bad in ((4, 4), (5, 2)):
            with pytest.raises(ValueError):
                m.Range(*bad)

    def test_d018_twin_allows_degenerate_range(self) -> None:
        t = _load("D018-exclusive-upper-bound", "twin")
        assert t.size(t.Range(5, 2)) == -3, "twin 이 음수 크기를 허용해야 한다"


class TestIdempotentRetry:
    """D010 — 재시도가 정말 멱등인가."""

    def test_d010_repeat_send_does_not_duplicate_the_side_effect(self) -> None:
        """🔴 _sent 가 아니라 _outbox 를 본다 - set 은 add 가 멱등이라
        상태 크기로는 「세 번 발송」이 보이지 않는다."""
        m = _load("D010-idempotent-retry")
        assert m.send("msg-1", "body")
        assert m._outbox == ["body"]
        assert m.send("msg-1", "body")
        assert m._outbox == ["body"], "재시도가 두 번째 발송을 만들었다"
