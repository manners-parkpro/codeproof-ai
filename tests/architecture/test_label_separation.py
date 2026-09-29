"""라벨 분리가 구조적으로 성립하는지.

tests/architecture/test_layering.py 가 "런타임은 eval 을 import 못 한다" 를 보고,
여기서는 그 결과로 **타입 수준에서 라벨이 도달 불가능한지** 를 본다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import codeproof_ai.domain as domain_pkg
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.sample import (
    Defect,
    DefectOrigin,
    LabeledSample,
    SafetyRationale,
    Stratum,
)

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _target(tid: str = "t1") -> ReviewTarget:
    return ReviewTarget(target_id=tid, files=(SourceFile("a.py", "x = 1\n"),))


def _defect() -> Defect:
    return Defect(
        location=Location(path="a.py", span=Span(Position(1, 0))),
        origin=DefectOrigin.INJECTED,
        description="x",
    )


class TestDomainCarriesNoLabels:
    def test_domain_exports_no_label_types(self) -> None:
        leaked = [
            n
            for n in domain_pkg.__all__
            if n in {"Defect", "LabeledSample", "Sample", "Stratum", "SafetyRationale"}
        ]
        assert not leaked, (
            f"domain 이 라벨 타입을 내보낸다: {leaked}. "
            "라벨은 eval/sample.py 에만 있어야 런타임이 볼 방법이 없다."
        )

    def test_review_target_has_no_defect_field(self) -> None:
        assert not hasattr(_target(), "defects")

    def test_review_target_knows_what_is_visible(self) -> None:
        """ReviewTarget.files 가 곧 '리뷰어가 볼 수 있는 전부' 다."""
        t = _target()
        assert t.is_visible("a.py", 1)
        assert not t.is_visible("a.py", 2)
        assert not t.is_visible("unseen.py", 1)

    def test_rejects_empty_and_duplicate_files(self) -> None:
        with pytest.raises(ValueError, match="파일이 없으면"):
            ReviewTarget(target_id="t", files=())
        with pytest.raises(ValueError, match="중복"):
            ReviewTarget(
                target_id="t",
                files=(SourceFile("a.py", "1"), SourceFile("a.py", "2")),
            )


class TestMutualExclusion:
    """🔴 결함이 있으면서 동시에 '증명된 안전' 일 수는 없다."""

    def test_defects_and_safety_cannot_coexist(self) -> None:
        with pytest.raises(ValueError, match="상호 배타"):
            LabeledSample(
                target=_target(),
                stratum=Stratum.DECOY,
                defects=(_defect(),),
                safety=SafetyRationale(claim="c", justification="j" * 30),
                paired_with="other",
            )

    def test_decoy_negative_requires_rationale(self) -> None:
        with pytest.raises(ValueError, match="SafetyRationale"):
            LabeledSample(
                target=_target(), stratum=Stratum.DECOY, paired_with="other"
            )

    def test_decoy_positive_needs_no_rationale(self) -> None:
        """twin 은 D층 양성이다 - 안전 근거 없이 성립해야 한다."""
        s = LabeledSample(
            target=_target(),
            stratum=Stratum.DECOY,
            defects=(_defect(),),
            paired_with="other",
        )
        assert not s.is_negative
        assert not s.is_proven_safe

    def test_paired_strata_require_a_partner(self) -> None:
        for stratum in (Stratum.DECOY, Stratum.PAIRED_FIX):
            with pytest.raises(ValueError, match="짝이 되는"):
                LabeledSample(
                    target=_target(),
                    stratum=stratum,
                    defects=(_defect(),),
                )


class TestDecoyToSamples:
    def test_one_decoy_becomes_a_pair(self) -> None:
        """decoy 1건 → (음성, 양성) 2건. 개수를 하드코딩하지 않는다 -
        코퍼스가 자라면 깨지는 단언은 구조를 검사하는 게 아니다."""
        valid = sum(
            1
            for d in DECOYS.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )
        samples = load_decoy_samples(DECOYS)
        assert valid > 0, "코퍼스가 비어 있다"
        assert len(samples) == valid * 2

    def test_pair_is_mutually_linked(self) -> None:
        by_id = {s.sample_id: s for s in load_decoy_samples(DECOYS)}
        for s in by_id.values():
            assert s.paired_with in by_id
            assert by_id[s.paired_with].paired_with == s.sample_id

    def test_each_side_sees_only_its_own_file(self) -> None:
        """🔴 리뷰어에게 decoy 와 twin 을 같이 보여주면 정답을 알려주는 것이다."""
        for s in load_decoy_samples(DECOYS):
            assert len(s.target.files) == 1

    def test_the_filename_does_not_say_which_side_it_is(self) -> None:
        """🔴 짝의 두 쪽이 **같은 파일명**을 보여야 한다.

        [실측] 전에는 `decoy.py` / `twin.py` 로 갈렸고, **바로 위 테스트가
        그걸 옳다고 고정**하고 있었다(`expected = "twin.py" if ... else "decoy.py"`).
        정적분석기는 파일명을 거의 안 보므로 숫자로는 드러나지 않았지만,
        `twin.py` 를 받은 LLM 은 「고장난 쪽」임을 읽고 없는 결함을 찾는다.

        에이전트 층을 열면서 드러났다 - **리뷰어 종류가 늘어야 보이는 편향**이다.

        🔴 상수 하나를 확인하는 것으로는 부족하다. 한쪽이 다른 상수를 쓰도록
           바뀌어도 통과하기 때문이다. **짝마다 서로 비교**한다.
        """
        by_id = {s.sample_id: s for s in load_decoy_samples(DECOYS)}
        assert by_id, "샘플이 없다 - 대조가 공허하다"

        mismatched: list[str] = []
        for s in by_id.values():
            assert s.paired_with is not None, f"{s.sample_id}: 짝이 없다"
            other = by_id[s.paired_with]
            if s.target.visible_paths != other.target.visible_paths:
                mismatched.append(
                    f"{s.sample_id}: {s.target.visible_paths} vs "
                    f"{other.target.visible_paths}"
                )
        assert not mismatched, (
            "짝의 두 쪽이 다른 파일명을 보여준다 - 파일명이 정답을 흘린다:\n  "
            + "\n  ".join(mismatched)
        )

        # 같기만 해서는 안 된다 - 이름 자체가 라벨을 암시하면 안 된다.
        leaky = ("decoy", "twin", "safe", "buggy", "good", "bad", "vuln", "fixed")
        offenders = [
            f"{s.sample_id}: {path}"
            for s in by_id.values()
            for path in s.target.visible_paths
            if any(w in path.lower() for w in leaky)
        ]
        assert not offenders, (
            f"파일명이 정답을 암시한다 (금칙어 {leaky}):\n  " + "\n  ".join(offenders)
        )

    def test_guard_is_inside_the_visible_file(self) -> None:
        """V4 의 타입 수준 대응 - 가드가 제시된 파일 안에 있어야 한다."""
        for s in load_decoy_samples(DECOYS):
            if not s.is_proven_safe:
                continue
            assert s.safety is not None
            loc = s.safety.guard_location
            assert loc is not None
            assert s.target.is_visible(loc.path, loc.line), (
                f"{s.sample_id}: 가드가 제시된 파일 밖이다 - decoy 로 성립하지 않는다"
            )

    def test_negative_and_positive_split(self) -> None:
        """음성과 양성이 정확히 반반이어야 짝 채점이 성립한다."""
        samples = load_decoy_samples(DECOYS)
        negatives = sum(s.is_negative for s in samples)
        positives = sum(not s.is_negative for s in samples)
        assert negatives == positives == len(samples) // 2
