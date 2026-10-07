"""생성 그림 - report 가 계산한 값을 SVG 로 그린다 (README · docs/RESULTS.md 가 싣는다).

🔴 계산하지 않는다 - 받은 값만 그린다 (E0 과 같은 원칙). 숫자는 `report` 와 같은 계산에서 온다.
🔴 같은 값이면 같은 바이트다 - 시각 · 난수를 넣지 않는다. `report --check` 가 대조한다 (F5b).
🔴 손으로 고치지 않는다 - 파일 첫 줄이 그렇게 말한다.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

if TYPE_CHECKING:
    from collections.abc import Sequence

BANNER = "<!-- 생성물 - `uv run codeproof report` 가 만든다. 손으로 고치지 않는다. -->"
WIDTH = 760
BAR = 420  # 막대 영역 폭
PAIR_BAR = 340  # 짝 그림은 오른쪽에 사다리 열을 둔다
LABEL_MIN = 22  # 이보다 좁은 막대 조각에는 숫자를 싣지 않는다
STYLE = """<style>
text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
       "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; fill: #1f2328; font-size: 12px; }
.bg { fill: #ffffff; } .muted { fill: #59636e; } .title { font-size: 16px; font-weight: 600; }
.strong { font-weight: 600; } .grid { stroke: #d1d9e0; stroke-width: 1; }
.safe { fill: #0969da; } .inj { fill: #bc4c00; }
.claude { fill: #8250df; } .codex { fill: #1a7f37; }
.pc { fill: #1a7f37; } .pv { fill: #bf8700; } .pb { fill: #8c959f; } .pr { fill: #cf222e; }
.whisker { stroke: #59636e; stroke-width: 2; } .zero { stroke: #cf222e; stroke-dasharray: 4 3; }
.loose { fill-opacity: 0.3; } .card { fill: #f6f8fa; stroke: #d1d9e0; }
.code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
text.guard { fill: #0969da; } text.bug { fill: #cf222e; } text.small { font-size: 11px; }
@media (prefers-color-scheme: dark) {
  text { fill: #e6edf3; } .bg { fill: #0d1117; } .muted { fill: #9198a1; }
  .grid { stroke: #3d444d; } .safe { fill: #4493f8; } .inj { fill: #f0883e; }
  .claude { fill: #ab7df8; } .codex { fill: #3fb950; }
  .pc { fill: #3fb950; } .pv { fill: #d29922; } .pb { fill: #656c76; } .pr { fill: #f85149; }
  .whisker { stroke: #9198a1; } .card { fill: #161b22; stroke: #3d444d; }
  text.muted { fill: #9198a1; } text.guard { fill: #4493f8; } text.bug { fill: #f85149; }
}
</style>"""


@dataclass(frozen=True, slots=True)
class Spread:
    """룰 선택 하나에서 같은 지적을 두 정의로 채점한 FP."""

    select: str
    findings: int
    safety_fp: int
    injected_fp: int

    @property
    def verdict(self) -> str:
        if self.safety_fp == self.injected_fp:
            return "일치"
        if self.safety_fp == 0:
            return "배수로 잴 수 없다"
        return f"{self.injected_fp / self.safety_fp:.1f}배"


@dataclass(frozen=True, slots=True)
class PairCounts:
    """한 채점 정의의 짝 판정 - 구별 · 과잉지적 · 미탐지 · 역전."""

    grader: str
    correct: int
    over_flag: int
    under_flag: int
    reversed_: int

    @property
    def total(self) -> int:
        return self.correct + self.over_flag + self.under_flag + self.reversed_

    @property
    def dominant(self) -> str:
        """가장 많은 판정 - 같으면 앞선 것 (P-C · P-V · P-B · P-R 순). 짝이 없으면 -."""
        counts = (self.correct, self.over_flag, self.under_flag, self.reversed_)
        return ("P-C", "P-V", "P-B", "P-R")[counts.index(max(counts))] if self.total else "-"


@dataclass(frozen=True, slots=True)
class PairRung:
    """짝 판정 사다리의 한 칸 - 룰 선택 · 채점 정의 · slack 하나의 판정 수."""

    select: str
    grader: str
    slack: int
    counts: PairCounts


@dataclass(frozen=True, slots=True)
class Estimate:
    """점추정과 95% 구간 (비율 또는 %p 차이 - 0~1 단위)."""

    label: str
    point: float
    lo: float
    hi: float


@dataclass(frozen=True, slots=True)
class Share:
    """한 리뷰어의 한 지표 - 선언한 매칭(slack 0)과 사다리 끝 slack 의 값 (0~1)."""

    strict: float
    loose: float


@dataclass(frozen=True, slots=True)
class ScoreRow:
    """점수판 한 줄 - 같은 짝 판정을 다시 묶은 지표 하나."""

    label: str
    meaning: str
    verdicts: tuple[str, ...]
    a: Share
    b: Share
    diff: Estimate
    """slack 0 의 a - b · 같은 짝 부트스트랩 95%."""
    stable: bool
    """slack 사다리 전체에서 차이의 방향과 판정이 같은가 (A2a)."""
    primary: bool = False

    @property
    def distinguishable(self) -> bool:
        return self.diff.lo > 0 or self.diff.hi < 0


@dataclass(frozen=True, slots=True)
class Scoreboard:
    """두 리뷰어의 점수판 - 첫 줄이 「짚음」이다 (허용 오차 줄이 그 줄을 읽는다)."""

    names: tuple[str, str]
    pairs: int
    runs: tuple[int, int]
    slacks: tuple[int, ...]
    rows: tuple[ScoreRow, ...]
    conditions: str = ""


@dataclass(frozen=True, slots=True)
class ExampleSide:
    """예시 짝의 리뷰어 하나 - 모든 회차 · 모든 slack 에서 같은 판정이다."""

    name: str
    verdict: str
    runs: int
    quote: str = ""
    """1회차의 그 판정을 만든 지적 - P-C 는 twin 의 TP, P-V · P-R 은 decoy 의 FP."""
    silent: bool = False
    """두 파일 모두 모든 회차에 지적이 없다."""


@dataclass(frozen=True, slots=True)
class Example:
    """규칙으로 고른 예시 짝 하나 - 가드가 바뀐 줄과 두 리뷰어의 판정."""

    pair_id: str
    kind: str
    lines: int
    removed: tuple[str, ...]
    added: tuple[str, ...]
    defect: str
    winner: ExampleSide
    loser: ExampleSide


def _t(x: float, y: float, text: str, cls: str = "", anchor: str = "start") -> str:
    klass = f' class="{cls}"' if cls else ""
    return f'<text x="{x:g}" y="{y:g}"{klass} text-anchor="{anchor}">{escape(text)}</text>'


def _rect(x: float, y: float, w: float, h: float, cls: str) -> str:
    return f'<rect class="{cls}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="2"/>'


def _svg(height: int, title: str, body: list[str]) -> str:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(title)}">'
    )
    frame = f'<rect class="bg" width="{WIDTH}" height="{height}" rx="8"/>'
    return "\n".join([BANNER, head, STYLE, frame, *body, "</svg>", ""])


def _width(value: int, top: int) -> float:
    """막대 폭 - 0 이 아니면 최소 2px 로 보이게 한다."""
    return 0 if value == 0 or top == 0 else max(2.0, round(value / top * BAR, 1))


def spread_svg(points: Sequence[Spread], negatives: int) -> str:
    """같은 지적 · 정의만 바꿨다 - 룰 선택마다 두 정의의 FP (결과 2 · 6)."""
    title = "같은 지적, 정답 정의만 바꿨다 — 증명 가능하게 안전한 코드 위의 FP"
    body = [
        _t(20, 30, title, "title"),
        _t(20, 50, f"Ruff 지적은 그대로이고 채점자만 다르다 · slack 0 · 음성 {negatives}쌍",
           "muted"),
    ]
    top = max((max(p.safety_fp, p.injected_fp) for p in points), default=0)
    y = 72
    for p in points:
        body += [
            _t(20, y + 18, f"--ruff-select {p.select}", "strong"),
            _t(20, y + 36, f"음성 위 지적 {p.findings}건", "muted"),
        ]
        for row, (fp, cls) in enumerate(((p.safety_fp, "safe"), (p.injected_fp, "inj"))):
            by = y + 6 + row * 22
            w = _width(fp, top)
            if w:
                body.append(_rect(190, by, w, 16, cls))
            body.append(_t(190 + w + 6, by + 12, str(fp)))
        body += [
            _t(WIDTH - 20, y + 18, f"{p.safety_fp} 대 {p.injected_fp}", "strong", "end"),
            _t(WIDTH - 20, y + 36, p.verdict, "muted", "end"),
        ]
        y += 60
    body += [
        _rect(20, y + 6, 12, 12, "safe"),
        _t(38, y + 16, "provable_safety — 근거 범위 안의 결함 주장만 FP"),
        _rect(380, y + 6, 12, 12, "inj"),
        _t(398, y + 16, "injected_defect — Qodo 정의, 판정 불가 칸이 없다"),
    ]
    return _svg(y + 36, title, body)


_SEGMENTS = (("correct", "pc", "P-C 구별"), ("over_flag", "pv", "P-V 과잉지적"),
             ("under_flag", "pb", "P-B 미탐지"), ("reversed_", "pr", "P-R 역전"))


def pairs_svg(rungs: Sequence[PairRung]) -> str:
    """같은 실행의 짝 판정 - 막대는 slack 0, 오른쪽은 slack 사다리의 주된 판정 (결과 3 · A2a).

    🔴 막대 하나로는 그 판정이 정의의 것인지 매칭 정책의 것인지 모른다 -
       사다리에서 가장 많은 판정이 바뀌면 「흔들린다」고 적는다.
    """
    title = "짝 판정도 채점 정의의 함수다 — 같은 Ruff 실행"
    rows: dict[tuple[str, str], list[PairRung]] = {}
    for r in rungs:
        rows.setdefault((r.select, r.grader), []).append(r)
    base = min((r.slack for r in rungs), default=0)
    slacks = sorted({r.slack for r in rungs})
    pairs = max((r.counts.total for r in rungs), default=0)
    body = [
        _t(20, 30, title, "title"),
        _t(20, 50, f"decoy(안전)와 twin(가드 제거) {pairs}쌍 · 막대는 slack {base} · "
           "오른쪽은 slack 마다 가장 많은 판정", "muted"),
        _t(WIDTH - 20, 84, "slack " + "·".join(map(str, slacks)), "muted", "end"),
    ]
    y, current = 72, ""
    for (select, grader), rs in rows.items():
        if select != current:
            y += 8 if current else 0
            body.append(_t(20, y + 12, f"--ruff-select {select}", "strong"))
            y, current = y + 20, select
        bar = min(rs, key=lambda r: r.slack).counts
        body.append(_t(20, y + 13, grader))
        x = 190.0
        for attr, cls, _label in _SEGMENTS:
            n = getattr(bar, attr)
            w = 0.0 if bar.total == 0 else round(n / bar.total * PAIR_BAR, 1)
            if w:
                body.append(_rect(x, y, w, 18, cls))
                if w >= LABEL_MIN:
                    body.append(_t(x + w / 2, y + 13, str(n), anchor="middle"))
            x += w
        tops = [r.counts.dominant for r in sorted(rs, key=lambda r: r.slack)]
        moved = len(set(tops)) > 1
        verdict = "·".join(tops)
        if bar.total:
            verdict += " 흔들린다" if moved else " 안정"
        body.append(_t(WIDTH - 20, y + 13, verdict, "strong" if moved else "muted", "end"))
        y += 26
    y += 8
    lx = 20.0
    for _attr, cls, label in _SEGMENTS:
        body += [_rect(lx, y + 6, 12, 12, cls), _t(lx + 18, y + 16, label)]
        lx += 130
    return _svg(y + 36, title, body)


def _x(v: float, lo: float, hi: float, x0: float, x1: float) -> float:
    return round(x0 + (v - lo) / (hi - lo) * (x1 - x0), 1)


def _pct(v: float, *, signed: bool = False) -> str:
    return f"{v * 100:+.1f}" if signed else f"{v * 100:.1f}"


def agents_svg(
    rates: Sequence[tuple[str, float]],
    ladder: Sequence[tuple[int, Estimate]],
    *,
    pairs: int,
    runs: Sequence[int],
) -> str:
    """에이전트 비교 - 두 리뷰어의 기대값과 같은 짝 위의 차이 · slack 사다리 (결과 7).

    🔴 리뷰어마다의 구간은 그리지 않는다 - 두 구간을 겹쳐 보는 읽기를 그림이 권하게 된다 (F6).
       구간은 같은 짝 위의 차이에만 있다 (생성물의 비교 표와 같은 관례).
    """
    title = "에이전트 비교 — 같은 짝 위의 차이로 낸다"
    n = "·".join(dict.fromkeys(map(str, runs)))
    body = [
        _t(20, 30, title, "title"),
        _t(20, 50, "구별 성공(P-C) 비율 · provable_safety · 단일 실행 기대값 (slack 0) · "
           f"{pairs}쌍 · 샘플당 {n}회 · 차이는 짝 부트스트랩 95% 구간", "muted"),
    ]
    x0, x1 = 200.0, 600.0
    y = 76
    for v in (0.0, 0.5, 1.0):
        x = _x(v, 0, 1, x0, x1)
        body += [f'<line class="grid" x1="{x:g}" y1="{y - 8}" x2="{x:g}" y2="{y + 52}"/>',
                 _t(x, y + 66, f"{v:.0%}", "muted", "middle")]
    body.append(_t(WIDTH - 20, y + 66, "비교는 아래의 차이로", "muted", "end"))
    for i, (label, point) in enumerate(rates):
        cy = y + 8 + i * 28
        cls = "claude" if "claude" in label else "codex"
        body += [
            _t(20, cy + 4, label),
            f'<circle class="{cls}" cx="{_x(point, 0, 1, x0, x1):g}" cy="{cy}" r="6"/>',
            _t(WIDTH - 20, cy + 4, f"{_pct(point)}%", anchor="end"),
        ]
    y += 104
    names = " - ".join(label for label, _ in rates)
    body.append(_t(20, y, f"차이 ({names}) · slack 사다리", "strong"))
    lo = min(-0.1, *(e.lo for _, e in ladder)) if ladder else -0.1
    hi = max(0.4, *(e.hi for _, e in ladder)) if ladder else 0.4
    zero = _x(0, lo, hi, x0, x1)
    top = y + 12
    for i, (slack, e) in enumerate(ladder):
        cy = top + 10 + i * 26
        lo_s, hi_s = _pct(e.lo, signed=True), _pct(e.hi, signed=True)
        diff = f"{_pct(e.point, signed=True)}%p [{lo_s}, {hi_s}]"
        body += [
            _t(20, cy + 4, f"slack {slack}"),
            f'<line class="whisker" x1="{_x(e.lo, lo, hi, x0, x1):g}" y1="{cy}" '
            f'x2="{_x(e.hi, lo, hi, x0, x1):g}" y2="{cy}"/>',
            f'<circle class="claude" cx="{_x(e.point, lo, hi, x0, x1):g}" cy="{cy}" r="5"/>',
            _t(WIDTH - 20, cy + 4, diff, anchor="end"),
        ]
    bottom = top + 10 + len(ladder) * 26
    body += [
        f'<line class="zero" x1="{zero:g}" y1="{top}" x2="{zero:g}" y2="{bottom - 10}"/>',
        _t(zero, bottom + 6, "0 — 구간이 0 을 품으면 구별되지 않는다", "muted", "middle"),
    ]
    return _svg(bottom + 26, title, body)


SCORE_BAR = 230  # 점수판 막대 폭 (0~100%)
CODE_LINES = 4  # 예시 한 쪽에 싣는 바뀐 줄 - 넘으면 … 한 줄로 줄인다


def _units(text: str) -> int:
    """표시 폭 - 한글 · 전각은 2칸이다."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def _clip(text: str, units: int) -> str:
    """표시 폭으로 자른다. SVG 글은 줄을 바꾸지 않아 넘치면 잘려 보인다."""
    flat = " ".join(text.split())
    if _units(flat) <= units:
        return flat
    used = 0
    for i, c in enumerate(flat):
        used += _units(c)
        if used > units - 1:
            return flat[:i].rstrip() + "…"
    return flat  # 닿지 않는다 - 위에서 폭이 units 를 넘었다


def _wrap(text: str, units: int) -> list[str]:
    """표시 폭으로 줄을 나눈다 - 공백에서만 끊는다. 낱말 하나가 넘치면 그 줄만 자른다."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        joined = f"{line} {word}" if line else word
        if line and _units(joined) > units:
            lines.append(line)
            line = word
        else:
            line = joined
    if line:
        lines.append(line)
    return [_clip(ln, units) for ln in lines]


def _bar(x: float, y: float, share: Share, cls: str) -> list[str]:
    """굵은 막대는 선언한 매칭(slack 0)의 값, 아래 가는 선은 사다리 끝 slack 의 값이다.

    🔴 두 값을 한 막대의 진하기로 겹치지 않는다 - 「짚음」은 넓히면 늘고 「놓침」은 줄어, 겹치면
       숫자가 막대의 어느 끝인지 줄마다 달라진다.
    """
    strict, loose = round(share.strict * SCORE_BAR, 1), round(share.loose * SCORE_BAR, 1)
    out = [_rect(x, y, max(strict, 2.0), 11, cls)] if strict else []
    if loose:
        out.append(_rect(x, y + 12, max(loose, 2.0), 3, f"{cls} loose"))
    return out


def scoreboard_svg(board: Scoreboard) -> str:
    """점수판 - 같은 짝 판정을 지표 넷으로 다시 묶었다 (README 첫 화면 · 생성물 「점수판」).

    🔴 리뷰어마다의 구간은 싣지 않는다 - 구간은 같은 짝 위의 차이에만 있다
       (F6 · `agents_svg` 와 같다).
    🔴 숫자는 선언한 매칭(slack 0)이고, 사다리 끝 slack 의 값을 줄마다 같이 싣는다 - 매칭 정책의
       몫을 숨기지 않는다 (A2a).
    """
    a, b = board.names
    loose = board.slacks[-1]
    n = "·".join(dict.fromkeys(map(str, board.runs)))
    title = f"{a} 와 {b} — 같은 코드를 리뷰했다"
    head = (
        f"안전한 판과 가드만 지운 판 {board.pairs}쌍 · 샘플당 {n}회 · "
        "한 번 돌렸을 때의 기대 비율 · 채점 provable_safety — 짚은 줄이 정답 자리와 겹쳐야 인정"
    )
    body = [_t(20, 30, title, "title")]
    y = 50
    for line in _wrap(head, 130):
        body.append(_t(20, y, line, "muted"))
        y += 18
    body += [
        _rect(20, y - 2, 12, 11, "claude"), _t(38, y + 8, a),
        _rect(140, y - 2, 12, 11, "codex"), _t(158, y + 8, b),
        _rect(250, y + 2, 24, 3, "pb loose"),
        _t(280, y + 8, f"가는 선 — 정답 자리에서 {loose}줄 안까지 인정하면", "muted"),
        _t(WIDTH - 20, y + 8, f"차이 ({a} - {b}) · 95%", "muted small", "end"),
    ]
    x0 = 230.0
    y += 24
    for row in board.rows:
        label = row.label + (" — 주 지표" if row.primary else "")
        body += [
            _t(20, y + 13, label, "strong"),
            _t(20, y + 30, _clip(row.meaning, 36), "muted small"),
        ]
        for i, (share, cls) in enumerate(((row.a, "claude"), (row.b, "codex"))):
            by = y + 1 + i * 18
            body += _bar(x0, by, share, cls)
            body += [
                _t(x0 + SCORE_BAR + 10, by + 10, f"{_pct(share.strict)}%"),
                _t(x0 + SCORE_BAR + 52, by + 10, f"{loose}줄 {_pct(share.loose)}%", "muted small"),
            ]
        e = row.diff
        verdict = "구별된다" if row.distinguishable else "구별되지 않는다"
        if not row.stable:
            verdict += " · slack 에 흔들린다"
        lo, hi = _pct(e.lo, signed=True), _pct(e.hi, signed=True)
        diff = f"{_pct(e.point, signed=True)}%p [{lo}, {hi}]"
        body += [
            _t(WIDTH - 20, y + 13, diff, "strong" if row.primary else "", "end"),
            _t(WIDTH - 20, y + 30, verdict, "muted", "end"),
        ]
        y += 50
    moved = [r.label for r in board.rows if not r.stable]
    ladder = "·".join(map(str, board.slacks))
    notes = [
        (
            f"차이의 판정은 허용 오차 {ladder}줄에서 모두 같다." if not moved
            else f"허용 오차 {ladder}줄에서 판정이 흔들린다: " + " · ".join(moved) + "."
        )
        + " 주 지표는 수집 전에 선언했고, 나머지 셋은 같은 짝 판정을 다시 묶은 보조다"
        " (다중 비교 보정 없음).",
        "차이의 구간은 같은 짝을 함께 복원추출한 부트스트랩이다.",
    ]
    if board.conditions:
        notes.append(f"조건: {board.conditions}")
    for note in notes:
        for line in _wrap(note, 130):
            body.append(_t(20, y + 6, line, "muted"))
            y += 18
    return _svg(y + 10, title, body)


_SIDE = {
    "P-C": "가드를 지운 판만 짚었다",
    "P-V": "안전한 판에도 경고했다",
    "P-B": "결함 자리를 짚지 못했다",
    "P-R": "안전한 판만 경고했다",
}


def _side(s: ExampleSide) -> str:
    what = "아무것도 지적하지 않았다" if s.silent else _SIDE.get(s.verdict, s.verdict)
    return f"{'✓' if s.verdict == 'P-C' else '✗'} {s.name} — {s.runs}회 모두 {what}"


def _code(lines: Sequence[str]) -> list[str]:
    if not lines:
        return ["(지운 줄)"]
    shown = list(lines[:CODE_LINES])
    if len(lines) > CODE_LINES:
        shown[-1] = "…"
    return shown


def examples_svg(examples: Sequence[Example], *, pairs: int, kinds: int) -> str:
    """무엇을 리뷰했나 - 규칙으로 고른 예시 짝 (랜딩 페이지 첫 그림 · 생성물 「점수판」의 예시).

    🔴 예시를 손으로 고르지 않는다 - 고르는 규칙은 `glance` 에 있고 그림에도 적는다.
    """
    title = "무엇을 리뷰했나 — 안전한 판과 가드만 지운 판"
    body = [
        _t(20, 30, title, "title"),
        _t(20, 50, f"직접 쓴 파이썬 코드 {pairs}쌍 · 함정 {kinds}종 · 리뷰어는 파일을 하나씩 받고, "
           "가드를 지운 판만 지적해야 한다", "muted"),
        _t(20, 68, "예시는 규칙으로 골랐다 — 한쪽은 모든 회차 · 허용 오차에서 정확히 가르고 "
           "다른 쪽은 늘 같은 오답을 낸 짝 중 decoy 가 가장 짧은 것", "muted small"),
    ]
    y = 82
    for ex in examples:
        top, cy = y, y + 44
        inner = [
            _t(36, y + 22, ex.pair_id, "strong"),
            _t(WIDTH - 36, y + 22, f"{ex.kind} · decoy {ex.lines}줄", "muted", "end"),
        ]
        for mark, lines, cls, side in (("-", ex.removed, "guard", "안전한 판"),
                                       ("+", ex.added, "bug", "가드를 지운 판")):
            for i, line in enumerate(_code(lines)):
                if i == 0:
                    inner.append(_t(36, cy, side, "muted small"))
                inner.append(_t(136, cy, f"{mark} {_clip(line, 82)}", f"code {cls}"))
                cy += 17
        defect = _clip(f"가드를 지운 판의 결함 — {ex.defect}", 112)
        inner.append(_t(36, cy + 3, defect, "muted small"))
        cy += 25
        for s in (ex.winner, ex.loser):
            inner.append(_t(36, cy, _side(s), "strong" if s is ex.winner else ""))
            cy += 17
            if s.quote:
                inner.append(_t(52, cy, f"“{_clip(s.quote, 106)}”", "muted small"))
                cy += 17
        height = cy - top
        body.append(
            f'<rect class="card" x="20" y="{top}" width="{WIDTH - 40}" height="{height}" rx="6"/>'
        )
        body += inner
        y = top + height + 12
    return _svg(y + 4, title, body)
