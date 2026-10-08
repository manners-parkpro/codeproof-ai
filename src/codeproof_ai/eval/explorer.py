"""기록된 리뷰 - 대시보드가 짝마다 두 리뷰어의 실제 지적을 보여 주는 데이터 (`docs/data/`).

🔴 JSON 이 아니라 전역 변수 하나를 정하는 스크립트다 - 받은 파일을 `file://` 로 열면 브라우저가
   fetch 를 막지만 고전 스크립트는 읽는다. 페이지는 Pages 와 받은 파일에서 같아야 한다.

🔴 새 측정이 아니다. 점수판과 같은 묶음 · 같은 채점(`provable_safety` · slack 0) · 같은 회차별
   다시 채점(`verdicts_by_run`)을 지적 단위로 펼친다. 회차마다 그 회차가 실제로 낸 원문을 싣고
   (`ObservedFinding.said_in` - 대표 지적은 다른 회차의 문구일 수 있다), 원문마다의 판정으로 다시
   만든 짝 판정이 점수판의 판정과 하나라도 다르면 만들지 않는다 - 화면이 센 값과 모순된다.
🔴 고르지 않는다 - 잰 짝 전부를 싣는다. 손으로 고른 예시는 결과를 고르는 것이다.
🔴 보여 주는 코드는 리뷰어가 실제로 본 내보내기다 (docstring 손잡이 그대로 · 줄 번호가 같다).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from codeproof_ai.analysis.python.ruff import SYNTAX_ERROR
from codeproof_ai.analysis.python.version import TARGET_PYTHON
from codeproof_ai.corpus.decoy import TrapKind
from codeproof_ai.domain.observation import ObservedFinding
from codeproof_ai.eval.export import neutral_docstring
from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.multirun import verdicts_by_run
from codeproof_ai.eval.pairing import PairVerdict
from codeproof_ai.eval.report import DISPLAY, HEADLINE_GRADER

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.domain.finding import Category, Finding
    from codeproof_ai.domain.location import Span
    from codeproof_ai.eval.report import AgentSection
    from codeproof_ai.eval.runner import SampleOutcome
    from codeproof_ai.eval.sample import LabeledSample

BANNER = "// 🔴 생성된 파일이다. 손으로 고치지 마라. `uv run codeproof report` 로 다시 만든다.\n"
REVIEWS = "reviews.js"
RUFF = "ruff.js"

KIND_LABELS: dict[TrapKind, str] = {
    TrapKind.UPSTREAM_VALIDATION: "앞에서 이미 검사했다",
    TrapKind.CALLER_HELD_LOCK: "부르는 쪽이 락을 쥔다",
    TrapKind.ENCLOSING_CONTEXT: "바깥 with 가 자원을 지킨다",
    TrapKind.CONTRACT_HALF_OPEN: "반열린 구간 계약",
    TrapKind.CONSTANT_ONLY_SINK: "위험 API 에 상수만 닿는다",
    TrapKind.TYPE_NARROWED: "타입이 이미 좁혀졌다",
    TrapKind.MISLEADING_NAME: "이름만 위험해 보인다",
    TrapKind.NOOP_SHIM_NEIGHBOR: "진짜 검사 옆의 빈 함수",
    TrapKind.UNREACHABLE_BRANCH: "닿지 않는 분기",
    TrapKind.IDEMPOTENT_RETRY: "재시도해도 결과가 같다",
    TrapKind.DEFENSIVE_COPY: "경계에서 복사본을 받는다",
    TrapKind.BOUNDED_INPUT: "입력 크기가 이미 묶였다",
    TrapKind.EXCEPTION_ABSORBED: "삼키는 것이 맞는 예외",
    TrapKind.FROZEN_AFTER_INIT: "초기화 뒤에는 바뀌지 않는다",
}
"""미끼 분류를 누구나 읽는 말로 - 분류마다 하나 (시험이 빠짐을 본다)."""

def _mark(outcome: Outcome, finding: Finding) -> str:
    """판정과 판정하지 않은 이유 - 관례 주장(`style`)과 정답 라벨 밖(`out`)을 가른다 (F4 · F4a).

    🔴 분류 규칙(`is_defect_claim`)을 화면에 다시 쓰지 않는다 - 여기서 한 번 정한다.
    """
    if outcome is Outcome.TRUE_POSITIVE:
        return "tp"
    if outcome is Outcome.FALSE_POSITIVE:
        return "fp"
    return "out" if finding.category.is_defect_claim else "style"


def _lines(span: Span) -> list[int]:
    """보고 범위의 첫 줄과 끝 줄 - `Span.overlaps` 와 같은 규칙 (끝이 없으면 첫 줄)."""
    last = span.end.line if span.end is not None else span.start.line
    return [span.start.line, max(span.start.line, last)]


def _said(
    outcome: SampleOutcome, sample: LabeledSample, run: int, grader: ProvableSafetyGrader
) -> list[list[object]]:
    """그 회차가 실제로 낸 원문과 원문마다의 판정 - `[시작 줄, 끝 줄, 분류, 판정, 내용]`.

    판정은 `tp` · `fp` · `style`(관례 주장 - 채점하지 않는다) · `out`(정답 라벨 밖).
    """
    rows: list[list[object]] = []
    for group in outcome.observations.in_run(run):
        for f in group.said_in(run):
            (j,) = grader.judge(sample, [ObservedFinding(f, frozenset({0}), 1)])
            mark = _mark(j.outcome, f)
            rows.append([*_lines(f.location.span), f.category.value, mark, f.message])
    return rows


def _verdict(safe: Sequence[Sequence[object]], buggy: Sequence[Sequence[object]]) -> PairVerdict:
    """원문마다의 판정으로 다시 만든 짝 판정 - `score_pairs` 와 같은 규칙."""
    alarm = any(row[3] == "fp" for row in safe)
    caught = any(row[3] == "tp" for row in buggy)
    if caught:
        return PairVerdict.OVER_FLAG if alarm else PairVerdict.CORRECT
    return PairVerdict.REVERSED if alarm else PairVerdict.UNDER_FLAG


def _code(sample: LabeledSample, docstrings: str) -> str:
    text = sample.target.files[0].content
    return neutral_docstring(text) if docstrings == "neutral" else text


def _reviews(
    section: AgentSection, samples: Sequence[LabeledSample], pairs: Sequence[str]
) -> dict[str, list[dict[str, object]]]:
    """짝마다 회차별 판정과 원문 - 짝 판정이 점수판과 다르면 거부한다."""
    grader = ProvableSafetyGrader(overlap_slack=0)
    official = verdicts_by_run(section.run.outcomes, samples, grader)
    by_id = {s.sample_id: s for s in samples}
    outs = {o.sample_id: o for o in section.run.outcomes}
    found: dict[str, list[dict[str, object]]] = {}
    for pid in pairs:
        runs: list[dict[str, object]] = []
        for r, verdicts in enumerate(official):
            safe = _said(outs[pid], by_id[pid], r, grader)
            twin = f"{pid}#twin"
            buggy = _said(outs[twin], by_id[twin], r, grader)
            mine = _verdict(safe, buggy)
            if mine is not verdicts[pid]:
                msg = (
                    f"{section.run.reviewer} {pid} 회차 {r}: 원문 판정으로 만든 짝 판정 "
                    f"{mine.value} 이 점수판의 {verdicts[pid].value} 와 다르다 - 화면이 센 값과 "
                    "모순된다"
                )
                raise ValueError(msg)
            runs.append({"verdict": mine.value, "safe": safe, "buggy": buggy})
        found[pid] = runs
    return found


def reviews(
    pair: tuple[AgentSection, AgentSection],
    samples: Sequence[LabeledSample],
    featured: Sequence[str] = (),
) -> str:
    """두 리뷰어가 잰 짝 전부의 기록 - 짝 하나가 한 줄 (diff 가 짝 단위로 읽힌다).

    `featured` 는 점수판의 예시 규칙이 고른 짝이다 - 화면이 처음 여는 짝도 손으로 고르지 않는다.
    """
    a = pair[0]
    measured = {o.sample_id for o in a.run.outcomes}
    by_id = {s.sample_id: s for s in samples}
    pairs = sorted(s.sample_id for s in samples if s.safety is not None and s.sample_id in measured)
    found = [_reviews(x, samples, pairs) for x in pair]
    rows = []
    for pid in pairs:
        safe, buggy = by_id[pid], by_id[f"{pid}#twin"]
        assert safe.safety is not None  # pairs 가 걸렀다
        guard, covered = safe.safety.guard_location, safe.safety.covered_lines
        defect = buggy.defects[0]
        rows.append({
            "id": pid,
            "kind": safe.safety.category,
            "claim": safe.safety.claim,
            "bug": defect.description,
            "safe": {
                "code": _code(safe, a.docstrings),
                "guard": _lines(guard.span) if guard else None,
                "covered": list(covered) if covered else None,
            },
            "buggy": {
                "code": _code(buggy, a.docstrings),
                "defect": _lines(defect.location.span),
            },
            "reviews": [f[pid] for f in found],
        })
    head = {
        "grading": {"grader": HEADLINE_GRADER, "slack": 0},
        "reviewers": [
            {
                "name": DISPLAY.get(x.agent, x.run.reviewer),
                "model": dict(x.setup).get("model", "?"),
                "version": dict(x.setup).get("cli_version", "?"),
                "runs": x.run.manifest.sample_n,
            }
            for x in pair
        ],
        "kinds": {k.value: label for k, label in KIND_LABELS.items()},
        "featured": [f for f in featured if f in pairs],
    }
    return _with_rows("CODEPROOF_REVIEWS", head, "pairs", rows)


def ruff_rules(version: str, categories: Mapping[str, Category]) -> str:
    """브라우저 Ruff 가 같은 판 · 같은 대상 판으로 돌고, 지적을 측정과 같은 분류로 나누게 하는 표.

    🔴 분류는 도구에 묻는다 (C2 · F4a) - 접두사로 짐작하지 않는다. 결함 주장이 아닌 룰만 싣는다.
       도구가 분류를 주지 않았으면 만들지 않는다 - 빈 표는 「전부 결함 주장」으로 읽힌다.
    ⚠ 구문 오류 코드도 싣는다 - 룰이 아니라 화면이 따로 센다 (어댑터와 같은 값).
    """
    if not categories:
        msg = "Ruff 가 룰 분류를 주지 않았다 - 빈 표는 모든 지적을 결함 주장으로 보이게 한다"
        raise ValueError(msg)
    head = {
        "version": version,
        "target": f"py{TARGET_PYTHON[0]}{TARGET_PYTHON[1]}",
        "syntax": SYNTAX_ERROR,
    }
    convention = sorted(code for code, cat in categories.items() if not cat.is_defect_claim)
    return _with_rows("CODEPROOF_RUFF", head, "convention", convention)


def _with_rows(name: str, head: Mapping[str, object], key: str, rows: Sequence[object]) -> str:
    """`window.<name> = {...};` - 머리는 한 덩어리, 행은 한 줄씩 (diff 가 행 단위로 읽힌다).

    결정적이어야 `--check` 가 최신인지 묻는다 (F5b) - 시각을 넣지 않는다.
    """
    dump = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows]
    body = json.dumps(head, ensure_ascii=False, indent=1)[:-2]
    data = body + f',\n "{key}": [\n' + ",\n".join(dump) + "\n ]\n}"
    return f"{BANNER}window.{name} = {data};\n"


def load(text: str) -> dict[str, Any]:
    """생성한 데이터 스크립트를 다시 읽는다 - 시험과 검사가 같은 규칙으로 읽는다."""
    head, _, data = text.partition(" = ")
    if not (text.startswith(BANNER) and head.startswith(BANNER + "window.")):
        msg = "생성한 데이터 스크립트가 아니다"
        raise ValueError(msg)
    loaded = json.loads(data.removesuffix(";\n"))
    if not isinstance(loaded, dict):
        msg = "데이터가 객체가 아니다"
        raise ValueError(msg)
    return loaded
