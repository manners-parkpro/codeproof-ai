"""twin 정답 구간의 보조 정의 - decoy 의 FP 구간(미끼~가드)과 대칭 (DESIGN §7.10c ③).

🔴 [실측] decoy 의 FP 구간은 미끼~가드인데 twin 의 정답은 바뀐 줄뿐이었다. 가드를 지우기만 한
   twin 에서는 「지운 자리 다음 줄」이 정답이 되어, 실패가 일어나는 줄(미끼)을 짚은 지적이
   slack 0 에서 빗나간다. 주 지표는 그대로 두고 보조로 같은 지적을 다시 채점한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from codeproof_ai.corpus.decoy import decoy_lines_in_twin, load_decoy
from codeproof_ai.eval.loader import decoy_to_samples, load_decoy_samples

if TYPE_CHECKING:
    from codeproof_ai.domain.location import Span

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _lines(span: Span) -> tuple[int, int]:
    return span.start.line, (span.end or span.start).line


def _decoy_dirs() -> list[Path]:
    return sorted(p for p in DECOYS.iterdir() if p.is_dir() and not p.name.startswith("_"))


class TestDecoyLinesInTwin:
    DECOY = "a\nb\nguard1\nguard2\nc\nd\n"
    TWIN = "a\nb\nc\nd\n"

    def test_lines_after_a_deletion_shift_up(self) -> None:
        assert decoy_lines_in_twin(self.DECOY, self.TWIN, 5, 6) == [3, 4]

    def test_deleted_lines_have_no_counterpart(self) -> None:
        """짐작으로 옮기면 정답 구간이 근거 없이 넓어진다."""
        assert decoy_lines_in_twin(self.DECOY, self.TWIN, 3, 4) == []
        assert decoy_lines_in_twin(self.DECOY, self.TWIN, 1, 2) == [1, 2], "대조군"

    def test_every_mapped_line_says_the_same_thing(self) -> None:
        """코퍼스 전체 - 옮긴 twin 줄은 decoy 의 그 줄과 내용이 같다."""
        checked = 0
        for d in _decoy_dirs():
            rec = load_decoy(d)
            a, b = rec.decoy_source.splitlines(), rec.twin_source.splitlines()
            for i in range(1, len(a) + 1):
                for j in decoy_lines_in_twin(rec.decoy_source, rec.twin_source, i, i):
                    assert b[j - 1] == a[i - 1], (d.name, i, j)
                    checked += 1
        assert checked > 0


class TestWidenedTwinLabel:
    def test_widening_changes_some_twins_and_no_decoys(self) -> None:
        base = {s.sample_id: s for s in load_decoy_samples(DECOYS)}
        wide = {s.sample_id: s for s in load_decoy_samples(DECOYS, widen_twin=True)}
        assert base.keys() == wide.keys()
        widened = 0
        for sid, s in base.items():
            if not s.defects:  # decoy - 증명된 음성
                assert wide[sid] == s, sid
                continue
            (a0, a1), (b0, b1) = (
                _lines(s.defects[0].location.span), _lines(wide[sid].defects[0].location.span)
            )
            assert b0 <= a0 and a1 <= b1, sid
            widened += (b0, b1) != (a0, a1)
        assert widened > 0, "대조군 - 넓어지는 twin 이 있어야 이 정의가 뭔가를 바꾼다"

    def test_it_reaches_the_lure(self) -> None:
        """넓힌 구간은 twin 줄 번호로 옮긴 미끼를 전부 덮는다 - decoy 의 미끼~가드와 대칭."""
        for d in _decoy_dirs():
            rec = load_decoy(d)
            lure = decoy_lines_in_twin(
                rec.decoy_source, rec.twin_source, rec.lure.start, rec.lure.end
            )
            _, twin = decoy_to_samples(rec, widen_twin=True)
            lo, hi = _lines(twin.defects[0].location.span)
            assert all(lo <= ln <= hi for ln in lure), d.name
