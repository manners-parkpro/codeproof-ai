"""한눈에 - 점수판과 예시 짝 (생성물 「점수판」 · 그림 scoreboard · examples).

🔴 새 측정이 아니다. 에이전트 비교와 같은 묶음 · 같은 채점(`provable_safety`)의 짝 판정을
   다시 묶는다 - 짚음(P-C · P-V) · 놓침(P-B · P-R) · 헛경고(P-V · P-R) · 정확히 짚음(P-C).
   주 지표는 마지막 하나이고 수집 전에 선언했다 (DESIGN §7.10b). 나머지 셋은 사후 보조다.

🔴 허용 오차(slack)를 하나로 고르지 않는다 - 값은 선언한 매칭(slack 0)이고, 사다리 끝 값과
   차이의 판정이 사다리 전체에서 같은지를 같이 싣는다 (A2a).

🔴 예시는 규칙으로 고른다 - 이긴 쪽은 모든 회차 · 모든 slack 에서 P-C, 진 쪽은 모든 회차 ·
   모든 slack 에서 같은 오답인 짝 가운데 decoy 가 가장 짧은 것 (같으면 식별자 순) · 방향마다 하나.
   [실측 · 150쌍] slack 0 하나로만 고르면 Codex 가 결함 바로 옆 줄에 낸 맞는 지적이 「놓침」으로
   세어진 짝이 뽑혔다 - 매칭 정책의 산물이 예시가 된다 (DESIGN 교훈 #65).

그 짝 자체도 규칙으로 찾아 싣는다 (`near_miss`) - 한 리뷰어가 slack 0 에서는 모든 회차 「놓침」이고
사다리 다음 칸에서는 모든 회차 「짚음」인 짝. 위치를 세는 규칙 하나가 판정을 바꾸는 사례다.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.eval.figures import Estimate, Example, ExampleSide, Scoreboard, ScoreRow, Share
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.multirun import difference_of, mean_share, verdicts_by_run
from codeproof_ai.eval.pairing import PairVerdict
from codeproof_ai.eval.sensitivity import DEFAULT_SWEEP

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.eval.runner import ReviewerRun
    from codeproof_ai.eval.sample import LabeledSample

    Verdicts = list[dict[str, PairVerdict]]

CAUGHT = (PairVerdict.CORRECT, PairVerdict.OVER_FLAG)
MISSED = (PairVerdict.UNDER_FLAG, PairVerdict.REVERSED)
ALARM = (PairVerdict.OVER_FLAG, PairVerdict.REVERSED)
PRIMARY = (PairVerdict.CORRECT,)
"""수집 전에 선언한 주 지표 - 구별 성공(P-C) (DESIGN §7.10b)."""

ROWS: tuple[tuple[str, str, tuple[PairVerdict, ...]], ...] = (
    ("버그를 짚었다", "버그 코드의 결함을 지적", CAUGHT),
    ("버그를 놓쳤다", "결함을 지적하지 못함", MISSED),
    ("안전한 코드에 헛경고", "안전한 코드에 결함이 있다고 함", ALARM),
    ("버그만 정확히 짚었다", "안전한 코드는 통과, 버그만 지적", PRIMARY),
)
"""점수판의 지표 - 누구나 읽는 말로 쓴다. 판정 묶음은 생성물 「점수판」 표에 같이 싣는다."""


@dataclass(frozen=True, slots=True)
class NearMiss:
    """결함 근처를 가리켰는데 slack 0 에서는 「놓침」인 짝 - 한 리뷰어가 모든 회차에서."""

    pair_id: str
    side: int
    """두 리뷰어 가운데 어느 쪽인가 (0 · 1)."""
    slack: int
    """이 slack 에서는 모든 회차가 「짚음」이다."""

def glance(
    a: ReviewerRun,
    b: ReviewerRun,
    samples: Sequence[LabeledSample],
    *,
    names: tuple[str, str],
    models: tuple[str, str],
    conditions: str = "",
) -> tuple[Scoreboard, tuple[Example, ...], NearMiss | None] | None:
    """두 리뷰어의 점수판 · 예시 · 근처 지적 사례. 값이 없으면 None (0 으로 그리지 않는다).

    근처 지적 사례는 「짚음」이 사다리에서 더 크게 움직이는 리뷰어에서 찾는다 - 첫 화면이 그
    리뷰어의 두 값을 함께 싣는다.
    """
    ladder = {
        s: (
            verdicts_by_run(a.outcomes, samples, ProvableSafetyGrader(overlap_slack=s)),
            verdicts_by_run(b.outcomes, samples, ProvableSafetyGrader(overlap_slack=s)),
        )
        for s in DEFAULT_SWEEP
    }
    strict, loose = ladder[DEFAULT_SWEEP[0]], ladder[DEFAULT_SWEEP[-1]]
    rows: list[ScoreRow] = []
    for label, meaning, verdicts in ROWS:
        hits = frozenset(verdicts)
        d = difference_of(*strict, hits)
        share_a, share_b = _share(strict[0], loose[0], hits), _share(strict[1], loose[1], hits)
        if d.point is None or d.interval is None or share_a is None or share_b is None:
            return None
        readings = {difference_of(*ladder[s], hits).reading for s in DEFAULT_SWEEP}
        rows.append(
            ScoreRow(
                label,
                meaning,
                tuple(v.value for v in verdicts),
                share_a,
                share_b,
                Estimate(f"slack {DEFAULT_SWEEP[0]}", d.point, *d.interval),
                stable=len(readings) == 1,
                primary=verdicts == PRIMARY,
            )
        )
    board = Scoreboard(
        names,
        models,
        pairs=len(strict[0][0]),
        runs=(a.manifest.sample_n, b.manifest.sample_n),
        slacks=DEFAULT_SWEEP,
        rows=tuple(rows),
        conditions=conditions,
    )
    caught = rows[0]
    side = 0 if caught.a.loose - caught.a.strict >= caught.b.loose - caught.b.strict else 1
    by_id = {s.sample_id: s for s in samples}
    lengths = {p: _length(by_id[p]) for p in strict[0][0]}
    near = near_miss(ladder, lengths, side)
    found = NearMiss(near, side, DEFAULT_SWEEP[1]) if near is not None else None
    return board, _examples((a, b), samples, ladder, names), found


def near_miss(
    ladder: Mapping[int, tuple[Verdicts, Verdicts]], lengths: Mapping[str, int], side: int
) -> str | None:
    """slack 0 에서는 모든 회차 「놓침」, 다음 칸에서는 모든 회차 「짚음」인 짝 중 가장 짧은 것.

    🔴 두 칸 모두 **모든 회차**다 - 한 회차만 옮겨 가는 짝은 실행 변동과 매칭 정책이 섞인다.
    """
    low, step = DEFAULT_SWEEP[0], DEFAULT_SWEEP[1]
    found = [
        (lengths[p], p)
        for p in sorted(lengths)
        if all(run[p] in MISSED for run in ladder[low][side])
        and all(run[p] in CAUGHT for run in ladder[step][side])
    ]
    return min(found)[1] if found else None


def _share(strict: Verdicts, loose: Verdicts, hits: frozenset[PairVerdict]) -> Share | None:
    """선언한 매칭(slack 0)의 값과 사다리 끝 값."""
    low, high = mean_share(strict, hits), mean_share(loose, hits)
    return None if low is None or high is None else Share(low, high)


def fixed(
    ladder: Mapping[int, tuple[Verdicts, Verdicts]], side: int, pid: str
) -> PairVerdict | None:
    """모든 slack · 모든 회차에서 같은 판정이면 그 판정, 아니면 None."""
    got = {run[pid] for pair in ladder.values() for run in pair[side]}
    return got.pop() if len(got) == 1 else None


def pick_examples(
    ladder: Mapping[int, tuple[Verdicts, Verdicts]], lengths: Mapping[str, int]
) -> list[tuple[str, int, PairVerdict]]:
    """예시 짝 고르기 - (짝 · 이긴 쪽 · 진 쪽의 판정). 방향마다 하나, 후보가 없으면 그 방향은 없다.

    이긴 쪽은 늘(모든 slack · 모든 회차) P-C, 진 쪽은 늘 같은 오답인 짝 가운데 decoy 가 가장
    짧은 것 - 같으면 식별자 순. 🔴 slack 0 의 판정만 보면 결함 옆 줄에 낸 맞는 지적이 「놓침」인
    짝이 뽑힌다.
    """
    picked: list[tuple[str, int, PairVerdict]] = []
    for win in (0, 1):
        found = [
            (lengths[p], p, lost)
            for p in sorted(lengths)
            if fixed(ladder, win, p) is PairVerdict.CORRECT
            and (lost := fixed(ladder, 1 - win, p)) not in (None, PairVerdict.CORRECT)
        ]
        if found:
            _, pid, lost = min(found)
            assert lost is not None  # 위의 조건이다
            picked.append((pid, win, lost))
    return picked


def _examples(
    runs: tuple[ReviewerRun, ReviewerRun],
    samples: Sequence[LabeledSample],
    ladder: Mapping[int, tuple[Verdicts, Verdicts]],
    names: tuple[str, str],
) -> tuple[Example, ...]:
    """고른 짝(`pick_examples`)에 바뀐 줄과 결함을 붙인다."""
    by_id = {s.sample_id: s for s in samples}
    measured = ladder[DEFAULT_SWEEP[0]][0][0]
    lengths = {p: _length(by_id[p]) for p in measured}
    out: list[Example] = []
    for pid, win, lost in pick_examples(ladder, lengths):
        lose = 1 - win
        decoy = by_id[pid]
        twin = by_id[decoy.paired_with or ""]
        removed, added = _changed(_source(decoy), _source(twin))
        out.append(
            Example(
                pair_id=pid,
                kind=decoy.safety.category if decoy.safety and decoy.safety.category else "",
                lines=lengths[pid],
                removed=removed,
                added=added,
                defect=_sentence(twin.defects[0].description) if twin.defects else "",
                winner=ExampleSide(
                    names[win], PairVerdict.CORRECT.value, runs[win].manifest.sample_n
                ),
                loser=ExampleSide(
                    names[lose], lost.value, runs[lose].manifest.sample_n,
                    silent=_silent(runs[lose], {pid, twin.sample_id}),
                ),
            )
        )
    return tuple(out)


def _source(sample: LabeledSample) -> str:
    return sample.target.files[0].content


def _length(sample: LabeledSample) -> int:
    """decoy 줄 수 - `splitlines()` 는 U+2028 에서도 끊어 쓰지 않는다."""
    return len(_source(sample).rstrip("\n").split("\n"))


def _changed(decoy: str, twin: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """가드가 바뀐 줄 (decoy 쪽 · twin 쪽) - 빈 줄은 빼고 공통 들여쓰기를 걷는다."""
    left, right = decoy.split("\n"), twin.split("\n")
    removed: list[str] = []
    added: list[str] = []
    matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            removed += left[i1:i2]
            added += right[j1:j2]
    shown = [ln for ln in (*removed, *added) if ln.strip()]
    indent = min((len(ln) - len(ln.lstrip()) for ln in shown), default=0)
    return (
        tuple(ln[indent:].rstrip() for ln in removed if ln.strip()),
        tuple(ln[indent:].rstrip() for ln in added if ln.strip()),
    )


def _silent(run: ReviewerRun, sample_ids: set[str]) -> bool:
    """그 샘플들에 모든 회차의 지적이 없다."""
    return all(not o.observations.observed for o in run.outcomes if o.sample_id in sample_ids)


def _sentence(text: str) -> str:
    """첫 문장 - 마침표 · 물음표 · 느낌표 뒤의 공백에서 끊는다."""
    flat = " ".join(text.split())
    m = re.match(r"(.+?[.!?])(?:\s|$)", flat)
    return m[1] if m else flat
