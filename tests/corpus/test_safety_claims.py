"""안전 근거가 **참인지** 실행으로 확인한다.

🔴 검증기(V2~V11)는 근거의 **형식**만 본다. 내용이 맞는지는 못 본다.
   [실측] D015 를 처음 쓸 때 Semaphore(4) 를 가드로 삼았는데 4 스레드 동시
   진입을 허용하므로 그 경쟁은 실제로 일어난다 - 안전 주장이 거짓이었고
   **11개 규칙을 전부 통과했다.**

   안전 주장이 거짓인 decoy 는 없는 것보다 나쁘다 - 맞는 지적을 FP 로 채점한다.

여기서는 decoy 를 **실제로 실행해서** 주장을 반증하려 시도한다.
전수는 불가능하다 - 반증 시도가 실패했다는 것이지 증명은 아니다.
그래도 형식 검사보다는 훨씬 강한 신호다.
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

    def test_d010_repeat_delivery_is_suppressed(self) -> None:
        m = _load("D010-idempotent-retry")
        assert m.send("msg-1", "body")
        before = len(m._sent)
        assert m.send("msg-1", "body")
        assert len(m._sent) == before, "같은 키가 두 번 기록됐다"

    def test_d010_twin_delivers_repeatedly(self) -> None:
        t = _load("D010-idempotent-retry", "twin")
        assert not t.send("msg-1", "")  # 빈 body → 3회 시도 후 실패
        assert "msg-1" in t._sent


class TestEveryDecoyHasAClaimTest:
    """🔴 근거를 실행으로 확인하지 않은 decoy 가 늘어나는 것을 막는다."""

    UNTESTED_BY_DESIGN = frozenset({
        # 동시성 - 단위 테스트로 경쟁을 재현할 수 없다. 코드 검토로 확인했다.
        "D003-caller-held-lock",
        "D015-caller-held-semaphore",
        # 자원 수명 - 파일·트랜잭션. 부수효과 확인이 무겁다.
        "D004-enclosing-context-manager",
        "D014-enclosing-transaction",
        # 경로 탈출 - 실제 파일시스템이 필요하다.
        "D008-noop-shim-neighbor",
        # 슬라이싱 - D018 이 같은 계약을 덮는다.
        "D005-half-open-contract",
        # 도달성 - D017 이 같은 성질을 덮는다.
        "D009-unreachable-legacy-branch",
    })

    def test_coverage_of_safety_claims(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        all_ids = {
            d.name for d in DECOYS.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        }
        tested = {i for i in all_ids if f'"{i}"' in source}
        gap = all_ids - tested - self.UNTESTED_BY_DESIGN
        assert not gap, (
            f"안전 근거를 실행으로 확인하지 않은 decoy: {sorted(gap)}. "
            "테스트를 쓰거나, 쓸 수 없는 이유를 UNTESTED_BY_DESIGN 에 적는다."
        )

    def test_exemptions_are_still_real(self) -> None:
        """면제 목록에 사라진 decoy 가 남아 있지 않은지."""
        all_ids = {
            d.name for d in DECOYS.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        }
        stale = self.UNTESTED_BY_DESIGN - all_ids
        assert not stale, f"없는 decoy 가 면제 목록에 있다: {sorted(stale)}"
