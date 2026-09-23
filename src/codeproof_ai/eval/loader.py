"""코퍼스 → 평가 샘플 변환.

작성 형식(corpus.decoy.DecoyRecord)과 평가 형식(LabeledSample)을 분리한 이유:
작성 쪽은 검증에 필요한 풍부한 메타데이터(미끼 위치·가드 위치·trap 분류)를 원하고,
평가 쪽은 층이 달라도 같은 모양이어야 한다. 한 타입으로 합치면
A·B·C 층에 쓰이지 않는 필드가 따라다닌다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.corpus.decoy import (
    DecoyLoadError,
    Level,
    load_decoy,
    twin_changed_lines,
    validate_decoy,
)
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.sample import (
    Defect,
    DefectOrigin,
    LabeledSample,
    SafetyRationale,
    Stratum,
)

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.corpus.decoy import DecoyRecord

DECOY_FILENAME = "decoy.py"
TWIN_FILENAME = "twin.py"


def _twin_id(decoy_id: str) -> str:
    return f"{decoy_id}#twin"


def decoy_to_samples(rec: DecoyRecord) -> tuple[LabeledSample, LabeledSample]:
    """decoy 1건을 (음성, 양성) 짝으로 펼친다.

    decoy.py 는 증명된 음성, twin.py 는 진짜 결함이다.
    둘은 가드만 다르므로 PrimeVul 짝 채점(P-C/P-V/P-B/P-R)이 성립한다 -
    과잉지적은 짝을 지어야만 보인다.

    🔴 각 샘플의 ReviewTarget 에는 **해당 파일 하나만** 들어간다.
       리뷰어에게 decoy 와 twin 을 같이 보여주면 정답을 알려주는 것이다.
    """
    guard_loc = Location(
        path=DECOY_FILENAME,
        span=Span(
            start=Position(line=rec.guard.start, column=0),
            end=Position(line=rec.guard.end, column=0),
        ),
        symbol=rec.guard_symbol,
    )

    negative = LabeledSample(
        target=ReviewTarget(
            target_id=rec.decoy_id,
            files=(SourceFile(path=DECOY_FILENAME, content=rec.decoy_source),),
        ),
        stratum=Stratum.DECOY,
        safety=SafetyRationale(
            claim=rec.claim,
            justification=rec.justification,
            guard_location=guard_loc,
            buggy_twin_id=_twin_id(rec.decoy_id),
            # 주장이 덮는 범위 = 미끼 구간 + 가드 구간.
            # 미끼는 "무엇이 결함처럼 보이는가", 가드는 "왜 아닌가" 다.
            covered_path=DECOY_FILENAME,
            covered_lines=(
                min(rec.lure.start, rec.guard.start),
                max(rec.lure.end, rec.guard.end),
            ),
        ),
        paired_with=_twin_id(rec.decoy_id),
    )

    # twin 의 결함 위치 = **가드가 제거된 자리**.
    # diff 의 twin 쪽 구간을 그대로 쓴다 - V9 가 그 구간이 가드를
    # 건드리는지 이미 강제했으므로, 이 위치는 정의상 결함 위치다.
    twin_span = twin_changed_lines(rec.decoy_source, rec.twin_source)
    twin_start = twin_span[0].start if twin_span else 1
    twin_end = twin_span[-1].end if twin_span else 1

    positive = LabeledSample(
        target=ReviewTarget(
            target_id=_twin_id(rec.decoy_id),
            files=(SourceFile(path=TWIN_FILENAME, content=rec.twin_source),),
        ),
        stratum=Stratum.DECOY,
        defects=(
            Defect(
                location=Location(
                    path=TWIN_FILENAME,
                    span=Span(
                        start=Position(line=twin_start, column=0),
                        end=Position(line=twin_end, column=0),
                    ),
                ),
                origin=DefectOrigin.INJECTED,
                description=rec.twin_defect,
                category=rec.trap_kind.value,
            ),
        ),
        paired_with=rec.decoy_id,
    )
    return negative, positive


def load_decoy_samples(corpus_root: Path) -> list[LabeledSample]:
    """decoy 코퍼스 전체를 평가 샘플로 펼친다.

    🔴 검증을 통과하지 못한 decoy 는 싣지 않는다.
       규격 미달 decoy 가 섞이면 FPR 이 오염된다.
    """
    # 🔴 없는 경로는 예외가 아니라 빈 결과다. 호출부(CLI)가 「샘플이 없다」로
    #    exit 2 를 내는데, 여기서 FileNotFoundError 가 터지면 그 경로를 못 탄다.
    if not corpus_root.is_dir():
        return []

    samples: list[LabeledSample] = []
    for d in sorted(p for p in corpus_root.iterdir() if p.is_dir()):
        if d.name.startswith("_"):
            continue
        try:
            rec = load_decoy(d)
        except DecoyLoadError:
            continue
        if any(v.level is Level.ERROR for v in validate_decoy(rec)):
            continue
        samples.extend(decoy_to_samples(rec))
    return samples
