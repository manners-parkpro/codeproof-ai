"""측정 뒤 FP 구간 지적 — 판정 입력을 뽑고 민감도를 낸다 (DESIGN §3.5 「측정 뒤 FP 구간 지적」).

    python scripts/fp_span_findings.py extract <출력 디렉터리> [--root results/agent]
    python scripts/fp_span_findings.py sensitivity <출력 디렉터리> <판정.jsonl ...> [--root ...]

extract 는 report 와 같은 재생(`_agent_sections`)으로 두 neutral 묶음을 채점해, 주 지표
채점자(`provable_safety` · slack 0)가 FP 로 판정한 지적을 `items.jsonl` 에 쓴다. 단위는
(샘플 · 지적 열쇠) — 주 지표가 지적을 세는 단위다 (`Judgment.finding_key`). 같은 열쇠는
리뷰어와 무관하게 한 항목이다.
🔴 `items.jsonl` 에는 리뷰어와 회차가 없다 — 판정하는 쪽이 claude 다 (F7). 누가 냈는지는
   `key.jsonl` 에 따로 두고 판정이 끝난 뒤에 연다.

sensitivity 는 판정 파일(한 줄에 {"id", "verdict"} · verdict 는 correct | wrong)마다 correct 인
열쇠의 FP 를 판정 불가로 바꾼 채점자로 주 지표(`difference` · claude - codex)를 다시 낸다.
빈 판정 파일이면 주 지표와 같아야 한다.

채점 전에 커밋했다 — 결과를 보고 계산을 고르지 않는다.
[실측 · 60쌍 · 097c370 의 옛 코퍼스와 묶음] 빈 판정이면 그때 공개된 주 지표와 같다
(+7.2%p · [-0.6, +16.1]) · 항목 34개를 전부 correct 로 두면 +18.9%p [+7.8, +30.0] 로
움직인다 - 감싼 채점자가 판정을 실제로 바꾼다.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from codeproof_ai.cli import _agent_sections
from codeproof_ai.eval.grading.base import Judgment, Outcome
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.multirun import Difference, difference
from codeproof_ai.eval.report import HEADLINE_GRADER

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.observation import ObservedFinding
    from codeproof_ai.eval.report import AgentSection
    from codeproof_ai.eval.sample import LabeledSample

REPO = Path(__file__).resolve().parents[1]
REVIEWERS = ("claude", "codex")  # RUN.json 의 agent · 주 지표의 차이 방향 (a - b) - report 와 같다
VERDICTS = frozenset({"correct", "wrong"})


def _pair(root: Path, samples: list[LabeledSample]) -> tuple[AgentSection, AgentSection]:
    sections = _agent_sections(root, samples)
    if sections is None:
        sys.exit("묶음을 재생하지 못했다 - report --check 가 거부하는 이유와 같다 (위 메시지)")
    neutral = {s.agent: s for s in sections if s.docstrings == "neutral"}
    missing = [r for r in REVIEWERS if r not in neutral]
    if missing:
        sys.exit(f"neutral 묶음이 없다: {missing}")
    return neutral[REVIEWERS[0]], neutral[REVIEWERS[1]]


def _item_id(sample_id: str, key: str) -> str:
    return "F" + hashlib.sha256(f"{sample_id}\0{key}".encode()).hexdigest()[:10]


def _extract(out: Path, root: Path) -> int:
    samples = load_decoy_samples(REPO / "corpus" / "decoys")
    items: dict[str, dict[str, object]] = {}
    who: list[dict[str, object]] = []
    for section in _pair(root, samples):
        for outcome in section.run.outcomes:
            if not outcome.is_proven_safe:
                continue
            by_key = {o.finding.fingerprint: o for o in outcome.observations.observed}
            for j in outcome.judgments.get(HEADLINE_GRADER, ()):
                if j.outcome is not Outcome.FALSE_POSITIVE:
                    continue
                o = by_key[j.finding_key]
                iid = _item_id(outcome.sample_id, j.finding_key)
                item = items.setdefault(iid, _blank(iid, outcome.sample_id, j.finding_key, o))
                _add_texts(item, o)
                who.append({"id": iid, "reviewer": section.agent, "runs": sorted(o.runs)})
    out.mkdir(parents=True, exist_ok=True)
    rows = sorted(items.values(), key=lambda r: (str(r["sample_id"]), str(r["id"])))
    _write(out / "items.jsonl", rows)
    _write(out / "key.jsonl", who)
    pairs = len({r["sample_id"] for r in rows})
    print(f"판정할 항목 {len(rows)} · 샘플 {pairs} - {out}/items.jsonl (리뷰어 · 회차 없음)")
    return 0


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    path.write_text(body, encoding="utf-8")


def _blank(iid: str, sample_id: str, key: str, o: ObservedFinding) -> dict[str, object]:
    span = o.finding.location.span
    end = span.end.line if span.end else span.start.line
    return {
        "id": iid, "sample_id": sample_id, "finding_key": key, "lines": [span.start.line, end],
        "category": o.finding.category.value, "texts": [], "quoted": [],
    }


def _add_texts(item: dict[str, object], o: ObservedFinding) -> None:
    texts, quoted = item["texts"], item["quoted"]
    assert isinstance(texts, list)
    assert isinstance(quoted, list)
    for f in o.variants or (o.finding,):
        if f.message not in texts:
            texts.append(f.message)
        if f.quoted_code and f.quoted_code not in quoted:
            quoted.append(f.quoted_code)


class _Corrected:
    """주 지표 채점자를 감싸 「맞는 지적」으로 판정된 열쇠의 FP 를 판정 불가로 바꾼다 (민감도)."""

    uses_llm_judge = False

    def __init__(
        self, inner: ProvableSafetyGrader, correct: frozenset[tuple[str, str]]
    ) -> None:
        self.inner, self.correct = inner, correct
        self.name, self.definition, self.emits = inner.name, inner.definition, inner.emits

    def judge(
        self, sample: LabeledSample, observed: Sequence[ObservedFinding]
    ) -> list[Judgment]:
        return [
            replace(j, outcome=Outcome.UNDECIDABLE, rationale="측정 뒤 판정에서 맞는 지적 (민감도)")
            if j.outcome is Outcome.FALSE_POSITIVE
            and (sample.sample_id, j.finding_key) in self.correct
            else j
            for j in self.inner.judge(sample, observed)
        ]


def _show(label: str, d: Difference) -> None:
    if d.point is None or d.interval is None:
        print(f"{label}: 짝 {d.pairs} · 값 없음")
        return
    lo, hi = d.interval
    verdict = "구별된다" if d.distinguishable else "구별되지 않는다"
    print(f"{label}: 짝 {d.pairs} · 차이 {d.point:+.1%} · 95% [{lo:+.1%}, {hi:+.1%}] · {verdict}")


def _sensitivity(out: Path, verdict_files: list[Path], root: Path) -> int:
    items = {
        r["id"]: (r["sample_id"], r["finding_key"])
        for r in map(json.loads, (out / "items.jsonl").read_text(encoding="utf-8").splitlines())
    }
    samples = load_decoy_samples(REPO / "corpus" / "decoys")
    a, b = _pair(root, samples)
    base = ProvableSafetyGrader(overlap_slack=0)
    _show("주 지표", difference(a.run.outcomes, b.run.outcomes, samples, base))
    for path in verdict_files:
        text = path.read_text(encoding="utf-8")
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        bad = [r for r in rows if r.get("id") not in items or r.get("verdict") not in VERDICTS]
        if bad:
            sys.exit(f"{path}: 모르는 id 이거나 verdict 가 correct | wrong 이 아니다 ({bad[:2]})")
        correct = frozenset(items[r["id"]] for r in rows if r["verdict"] == "correct")
        print(f"{path.name}: 판정 {len(rows)}/{len(items)} · correct {len(correct)}")
        fixed = _Corrected(base, correct)
        d = difference(a.run.outcomes, b.run.outcomes, samples, fixed)
        _show("  correct 를 판정 불가로", d)
    return 0


def main(argv: list[str]) -> int:
    root = REPO / "results" / "agent"
    if "--root" in argv:
        i = argv.index("--root")
        root = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    command, *rest = argv or [""]
    if command == "extract" and rest:
        return _extract(Path(rest[0]), root)
    if command == "sensitivity" and len(rest) > 1:
        return _sensitivity(Path(rest[0]), [Path(p) for p in rest[1:]], root)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
