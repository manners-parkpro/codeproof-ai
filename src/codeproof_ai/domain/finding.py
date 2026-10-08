"""지적(Finding) — 정적분석기와 LLM 이 공통으로 산출하는 단위."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from codeproof_ai.domain.location import Location


class Severity(StrEnum):
    """정규화된 심각도.

    도구 원본 값(ruff 의 info|warning|error|fatal, mypy 의 error|note)은
    어댑터에서 이 집합으로 매핑한다. 원본 문자열을 그대로 흘리지 않는다.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class Category(StrEnum):
    """지적의 성격.

    실제 리뷰 코멘트 중 결함 지적은 14% 뿐이고 최대 범주는 코드 개선이다
    (Bacchelli & Bird). 결함만 담는 스키마를 쓰면 리뷰의 7/8 을 버린다.
    """

    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TYPE_SAFETY = "type_safety"
    RESOURCE = "resource"
    CONCURRENCY = "concurrency"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    OTHER = "other"

    @property
    def is_defect_claim(self) -> bool:
        """이 지적이 **결함을 주장**하는가, 아니면 관례를 주장하는가.

        🔴 채점에서 갈리는 경계다. 안전 근거는 「이 결함처럼 보이는 것이
        왜 결함이 아닌가」를 말하므로, **관례 주장은 반박할 수 없다.**

        [실측] 이 구분을 빼먹었을 때 `provable_safety` 의 FP 66건 중 **45건이
        `D103`(docstring 누락)** 이었다. decoy 함수에 정말 docstring 이 없으니
        그 지적은 옳다 - 그걸 FP 로 센 것은 **우리가 비판하는 바로 그 오류**다
        (증거의 부재를 오답으로 채점하는 것과 같은 종류).

        ⚠ `OTHER` 는 결함 주장으로 친다. 모델 지적은 분류가 비어 올 수 있는데,
          그걸 관례로 취급하면 **모델의 FP 가 조용히 사라진다.**
        """
        return self is not Category.STYLE


_WS = re.compile(r"\s+")


def _normalize_snippet(snippet: str) -> str:
    """공백을 접고 소문자화한다 — 포매팅 차이로 지문이 갈리지 않게."""
    return _WS.sub(" ", snippet).strip().lower()


@dataclass(frozen=True, slots=True)
class Finding:
    """단일 지적.

    🔴 fingerprint 에 라인 번호를 쓰지 않는다 (CLAUDE.md B2).
       쓰면 위쪽 줄만 고쳐도 모든 지적이 새 지적이 된다.

    Attributes:
        source: 산출 주체. "ruff" | "mypy" | "custom" | provider id.
        rule_id: 도구 룰 식별자. ruff 는 "F401", mypy 는 "attr-defined".
            LLM 지적은 프롬프트가 정의한 슬러그.
        message: 사람이 읽는 설명.
        location: 정규화된 위치.
        category: 정규화된 성격.
        severity: 정규화된 심각도.
        quoted_code: 모델이 인용한 문제 코드 원문.
            런타임 인용 검증(verify/citation.py)의 입력이다.
            정적분석기 산출에는 없을 수 있다.
        rule_name: 사람이 읽는 룰 이름 (ruff 의 "unused-import").
        hint: 부가 설명. mypy 의 note 가 여기 접혀 들어온다.
        suppression: noqa / type: ignore 등 억제 마커.
        raw: 도구 원본 페이로드. 🔴 절대 버리지 않는다 —
            정규화가 틀렸을 때 사후 재계산의 유일한 근거다.
    """

    source: str
    rule_id: str
    message: str
    location: Location
    category: Category = Category.OTHER
    severity: Severity = Severity.WARNING
    quoted_code: str | None = None
    rule_name: str | None = None
    hint: str | None = None
    suppression: str | None = None
    raw: dict[str, object] = field(default_factory=dict, compare=False, repr=False)

    @property
    def fingerprint(self) -> str:
        """라인 번호를 배제한 안정 식별자.

        (rule_id, 경로, 둘러싼 심볼, 정규화된 인용문) 로 구성한다 (B2). 경로는 줄 번호와 달리
        위쪽 편집에 흔들리지 않고, 다른 파일의 같은 지적을 가른다.
        SARIF 출력 시 partialFingerprints 에 싣는다 — fingerprints 가 아니다.
        """
        parts = (
            self.rule_id,
            self.location.path,
            self.location.symbol or "<module>",
            _normalize_snippet(self.quoted_code or ""),
        )
        digest = hashlib.blake2b("\x00".join(parts).encode("utf-8"), digest_size=16)
        return digest.hexdigest()

    def with_symbol(self, symbol: str | None, symbol_kind: str | None) -> Self:
        """AST 패스가 채운 둘러싼 심볼을 붙인 사본을 반환한다."""
        return replace(
            self,
            location=replace(self.location, symbol=symbol, symbol_kind=symbol_kind),
        )
