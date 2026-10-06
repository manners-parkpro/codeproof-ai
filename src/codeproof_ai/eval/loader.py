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
    decoy_lines_in_twin,
    load_decoy,
    pair_dirs,
    twin_changed_lines,
    validate_decoy,
)
from codeproof_ai.corpus.shape import classify
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

PRESENTED_FILENAME = "module.py"
"""🔴 리뷰어가 보는 파일명 - decoy 와 twin 이 **같은 이름**이어야 한다.

파일명이 `decoy.py` / `twin.py` 로 갈리면 그 자체가 **정답 라벨의 유출**이다.
정적분석기는 파일명을 거의 안 보지만 LLM 은 반드시 본다 - `twin.py` 를 받은
모델은 「이건 고장난 쪽이구나」를 읽고 없는 결함을 찾아내려 한다.

[실측] 에이전트 층(`ReviewerKind.AGENT`)을 열면서 코퍼스를 내보내다 발견했다.
정적분석기만 돌리던 동안에는 드러나지 않았다 - **리뷰어 종류가 늘어야 보이는
종류의 편향**이고, 그래서 층을 늘리는 일이 코퍼스 검증이기도 하다.

⚠ 이 이름은 합성 티가 난다. 그걸 감수하는 이유: 짝의 두 쪽이 **반드시 같아야**
  하는데, decoy 마다 다른 이름을 붙이려면 그 이름을 meta.toml 에 적게 되고
  (손으로 적는 축은 틀린다, F5a), 한쪽만 고쳐도 아무도 모른다.
"""


def _twin_id(decoy_id: str) -> str:
    return f"{decoy_id}#twin"


def decoy_to_samples(
    rec: DecoyRecord, *, widen_twin: bool = False
) -> tuple[LabeledSample, LabeledSample]:
    """decoy 1건을 (음성, 양성) 짝으로 펼친다.

    decoy.py 는 증명된 음성, twin.py 는 진짜 결함이다.
    둘은 가드만 다르므로 PrimeVul 짝 채점(P-C/P-V/P-B/P-R)이 성립한다 -
    과잉지적은 짝을 지어야만 보인다.

    🔴 각 샘플의 ReviewTarget 에는 **해당 파일 하나만** 들어간다.
       리뷰어에게 decoy 와 twin 을 같이 보여주면 정답을 알려주는 것이다.

    Args:
        widen_twin: twin 의 정답 구간을 decoy 처럼 넓힌다 - 보조 정의 (DESIGN §7.10c ③).
            주 지표는 이 정의를 쓰지 않는다.
    """
    guard_loc = Location(
        path=PRESENTED_FILENAME,
        span=Span(
            start=Position(line=rec.guard.start, column=0),
            end=Position(line=rec.guard.end, column=0),
        ),
        symbol=rec.guard_symbol,
    )

    negative = LabeledSample(
        target=ReviewTarget(
            target_id=rec.decoy_id,
            files=(SourceFile(path=PRESENTED_FILENAME, content=rec.decoy_source),),
        ),
        stratum=Stratum.DECOY,
        safety=SafetyRationale(
            claim=rec.claim,
            justification=rec.justification,
            guard_location=guard_loc,
            buggy_twin_id=_twin_id(rec.decoy_id),
            # 주장이 덮는 범위 = 미끼 구간 + 가드 구간.
            # 미끼는 "무엇이 결함처럼 보이는가", 가드는 "왜 아닌가" 다.
            covered_path=PRESENTED_FILENAME,
            covered_lines=(
                min(rec.lure.start, rec.guard.start),
                max(rec.lure.end, rec.guard.end),
            ),
            category=rec.trap_kind.value,
            # 🔴 도출한다 - meta.toml 에 필드를 더하지 않는다.
            shape=classify(
                rec.decoy_source, rec.lure.start, rec.guard_symbol
            ).value,
        ),
        paired_with=_twin_id(rec.decoy_id),
    )

    # twin 의 결함 위치 = **가드가 제거된 자리**.
    # diff 의 twin 쪽 구간을 그대로 쓴다 - V9 가 그 구간이 가드를
    # 건드리는지 이미 강제했으므로, 이 위치는 정의상 결함 위치다.
    twin_span = twin_changed_lines(rec.decoy_source, rec.twin_source)
    twin_start = twin_span[0].start if twin_span else 1
    twin_end = twin_span[-1].end if twin_span else 1
    if widen_twin:
        # 🔴 [실측] decoy 의 FP 구간은 미끼~가드인데 twin 의 정답은 바뀐 줄뿐이었다 - 가드를
        #    지우기만 한 twin 20/60 에서는 「지운 자리 다음 줄」이 정답이 된다. 미끼를 twin 줄
        #    번호로 옮겨 바뀐 줄과 잇는다 (decoy 쪽과 대칭). 못 옮기면 바뀐 줄만 쓴다.
        lure = decoy_lines_in_twin(
            rec.decoy_source, rec.twin_source, rec.lure.start, rec.lure.end
        )
        if lure:
            twin_start, twin_end = min(twin_start, *lure), max(twin_end, *lure)

    positive = LabeledSample(
        target=ReviewTarget(
            target_id=_twin_id(rec.decoy_id),
            files=(SourceFile(path=PRESENTED_FILENAME, content=rec.twin_source),),
        ),
        stratum=Stratum.DECOY,
        defects=(
            Defect(
                location=Location(
                    path=PRESENTED_FILENAME,
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


def load_decoy_samples(corpus_root: Path, *, widen_twin: bool = False) -> list[LabeledSample]:
    """decoy 코퍼스 전체를 평가 샘플로 펼친다.

    🔴 검증을 통과하지 못한 decoy 는 싣지 않는다.
       규격 미달 decoy 가 섞이면 FPR 이 오염된다.

    Args:
        widen_twin: twin 정답 구간의 보조 정의 (`decoy_to_samples`).
    """
    # 🔴 없는 경로는 예외가 아니라 빈 결과다 (`pair_dirs`). 호출부(CLI)가 「샘플이 없다」로
    #    exit 2 를 내는데, 여기서 FileNotFoundError 가 터지면 그 경로를 못 탄다.
    samples: list[LabeledSample] = []
    for d in pair_dirs(corpus_root):
        try:
            rec = load_decoy(d)
        except DecoyLoadError:
            continue
        if any(v.level is Level.ERROR for v in validate_decoy(rec)):
            continue
        samples.extend(decoy_to_samples(rec, widen_twin=widen_twin))
    return samples
