"""생성 그림 - report 가 계산한 값을 SVG 로 그린다 (README · docs/RESULTS.md 가 싣는다).

🔴 계산하지 않는다 - 받은 값만 그린다 (E0 과 같은 원칙). 숫자는 `report` 와 같은 계산에서 온다.
🔴 같은 값이면 같은 바이트다 - 시각 · 난수를 넣지 않는다. `report --check` 가 대조한다 (F5b).
🔴 손으로 고치지 않는다 - 파일 첫 줄이 그렇게 말한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

if TYPE_CHECKING:
    from collections.abc import Sequence

BANNER = "<!-- 생성물 - `uv run codeproof report` 가 만든다. 손으로 고치지 않는다. -->"
WIDTH = 760
BAR = 420  # 막대 영역 폭
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
@media (prefers-color-scheme: dark) {
  text { fill: #e6edf3; } .bg { fill: #0d1117; } .muted { fill: #9198a1; }
  .grid { stroke: #3d444d; } .safe { fill: #4493f8; } .inj { fill: #f0883e; }
  .claude { fill: #ab7df8; } .codex { fill: #3fb950; }
  .pc { fill: #3fb950; } .pv { fill: #d29922; } .pb { fill: #656c76; } .pr { fill: #f85149; }
  .whisker { stroke: #9198a1; }
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


@dataclass(frozen=True, slots=True)
class Estimate:
    """점추정과 95% 구간 (비율 또는 %p 차이 - 0~1 단위)."""

    label: str
    point: float
    lo: float
    hi: float


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
        _t(20, 50, f"Ruff 지적은 그대로이고 채점자만 다르다 · 음성 {negatives}쌍", "muted"),
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


def pairs_svg(groups: Sequence[tuple[str, Sequence[PairCounts]]]) -> str:
    """같은 실행의 짝 판정 - 정의마다 실패의 모양이 다르다 (결과 3)."""
    title = "짝 판정도 채점 정의의 함수다 — 같은 Ruff 실행"
    body = [
        _t(20, 30, title, "title"),
        _t(20, 50, "decoy(안전)와 twin(가드 제거)을 짝으로 놓고 정의마다 판정했다", "muted"),
    ]
    y = 72
    for select, rows in groups:
        body.append(_t(20, y + 12, f"--ruff-select {select}", "strong"))
        y += 20
        for r in rows:
            body.append(_t(20, y + 13, r.grader))
            x = 190.0
            for attr, cls, _label in _SEGMENTS:
                n = getattr(r, attr)
                w = 0.0 if r.total == 0 else round(n / r.total * BAR, 1)
                if w:
                    body.append(_rect(x, y, w, 18, cls))
                    if w >= LABEL_MIN:
                        body.append(_t(x + w / 2, y + 13, str(n), anchor="middle"))
                x += w
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


def agents_svg(rates: Sequence[Estimate], ladder: Sequence[tuple[int, Estimate]]) -> str:
    """에이전트 비교 - 두 리뷰어의 기대값과 같은 짝 위의 차이 · slack 사다리 (결과 7)."""
    title = "에이전트 비교 — 같은 짝 위의 차이로 낸다"
    body = [
        _t(20, 30, title, "title"),
        _t(20, 50, "provable_safety · 단일 실행 기대값 · 짝 부트스트랩 95% 구간", "muted"),
    ]
    x0, x1 = 200.0, 600.0
    y = 76
    for v in (0.0, 0.5, 1.0):
        x = _x(v, 0, 1, x0, x1)
        body += [f'<line class="grid" x1="{x:g}" y1="{y - 8}" x2="{x:g}" y2="{y + 52}"/>',
                 _t(x, y + 66, f"{v:.0%}", "muted", "middle")]
    for i, e in enumerate(rates):
        cy = y + 8 + i * 28
        cls = "claude" if "claude" in e.label else "codex"
        body += [
            _t(20, cy + 4, e.label),
            f'<line class="whisker" x1="{_x(e.lo, 0, 1, x0, x1):g}" y1="{cy}" '
            f'x2="{_x(e.hi, 0, 1, x0, x1):g}" y2="{cy}"/>',
            f'<circle class="{cls}" cx="{_x(e.point, 0, 1, x0, x1):g}" cy="{cy}" r="6"/>',
            _t(WIDTH - 20, cy + 4, f"{_pct(e.point)}% [{_pct(e.lo)}, {_pct(e.hi)}]", anchor="end"),
        ]
    y += 104
    names = " - ".join(e.label for e in rates)
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
