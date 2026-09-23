"""실행 매니페스트 — 재현성의 최소 단위.

🔴 manifest 없는 결과는 저장하지 않는다 (CLAUDE.md E1).
   store/ 는 경고가 아니라 **거부**해야 한다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class ToolVersion:
    """외부 도구 버전. ruff 는 pre-1.0 이라 정확히 핀해야 한다."""

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class RunManifest:
    """한 번의 실험 실행을 재현하는 데 필요한 전부.

    3개월 뒤 이 숫자를 재현할 수 없으면 실험이 아니다.

    Attributes:
        model_id: 정확한 모델 ID. 별칭 금지.
            날짜 없는 Claude ID 도 그 자체가 스냅샷이다 (4.6 세대 이후).
        prompt_hash: 프롬프트 파일 내용 해시. 프롬프트는 코드가 아니라 데이터다.
        corpus_hash: 코퍼스 스냅샷 해시.
        effort: 🔴 명시값. None 이면 안 된다 — 기본값이 모델마다 다르다 (L4).
            claude-opus-5-5 는 medium, claude-sonnet-5 는 high.
        sample_n: 반복 횟수. Anthropic 은 seed 도 temperature 도 없으므로
            재현성은 반복 + 오차막대로만 확보된다 (E4).
        params_sent: 실제로 보낸 파라미터.
        params_omitted: 🔴 **의도적으로 생략한** 파라미터.
            리뷰어는 보낸 것만큼 안 보낸 것도 알아야 한다.
        cache_policy: "nonce" | "cold_only". 캐싱 비대칭 대응 (L3).
        grouper: 🔴 "같은 지적인가" 판정 정책. 이것 자체가 측정 선택이다 -
            정책이 느슨하면 출현율이 올라간다. 기록하지 않으면
            다회 샘플링 결과를 재현할 수 없다.
        harness_sha: 하네스 git SHA.
        client_region: 지연 측정은 리전에 민감하다.
        tool_versions: 정적분석 도구 버전.
    """

    model_id: str
    prompt_hash: str
    corpus_hash: str
    effort: str
    sample_n: int
    cache_policy: str
    grouper: str
    harness_sha: str
    created_at: datetime
    client_region: str | None = None
    params_sent: dict[str, object] = field(default_factory=dict)
    params_omitted: tuple[str, ...] = field(default_factory=tuple)
    tool_versions: tuple[ToolVersion, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.effort:
            msg = "effort 는 명시해야 한다 — 기본값이 모델마다 다르다 (L4)"
            raise ValueError(msg)
        if self.sample_n < 1:
            msg = f"sample_n 은 1 이상이다: {self.sample_n}"
            raise ValueError(msg)
        if self.cache_policy not in {"nonce", "cold_only"}:
            msg = f"cache_policy 는 nonce|cold_only 다: {self.cache_policy}"
            raise ValueError(msg)
        if not self.grouper:
            msg = "grouper 는 명시해야 한다 - 출현율이 이 정책에 달려 있다"
            raise ValueError(msg)

    def _config_fields(self) -> dict[str, object]:
        """실행 **설정**. 시각과 무관한 것만 담는다."""
        return {
            "model_id": self.model_id,
            "prompt_hash": self.prompt_hash,
            "corpus_hash": self.corpus_hash,
            "effort": self.effort,
            "sample_n": self.sample_n,
            "cache_policy": self.cache_policy,
            "grouper": self.grouper,
            "harness_sha": self.harness_sha,
            "params_sent": self.params_sent,
            "params_omitted": list(self.params_omitted),
            "tool_versions": [[t.name, t.version] for t in self.tool_versions],
        }

    @property
    def config_hash(self) -> str:
        """🔴 시각을 뺀 설정 지문.

        같은 config_hash 의 두 실행을 비교하면 무엇이 드러나는가:

          정적분석기 - 결과가 다르면 **재현돼야 할 것이 안 된 것**이다.
                       도구 버전이나 환경이 조용히 바뀌었다는 신호다.
          모델      - 결과가 다른 것이 **정상**이다 (seed 도 temperature 도 없다).
                       그 차이의 크기가 곧 측정 대상이다.

        필드 하나로 두 경우를 다 다룬다.
        """
        payload = json.dumps(
            self._config_fields(), sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()

    @property
    def run_id(self) -> str:
        """이 **한 번의 실행**을 가리키는 id. 설정 + 시각."""
        payload = json.dumps(
            {"config": self.config_hash, "created_at": self.created_at.isoformat()},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()

    def disclosure_block(self) -> str:
        """리뷰어가 검증할 수 있는 형태의 공개 블록.

        🔴 첫 벤치마크 실행 **전에** 이게 동작해야 한다.
           없으면 무효화 사유 대부분이 리뷰어에게 보이지 않는다.
        """
        lines = [
            f"model_id      : {self.model_id}",
            f"effort        : {self.effort}  (명시값)",
            f"sample_n      : {self.sample_n}",
            f"cache_policy  : {self.cache_policy}",
            f"grouper       : {self.grouper}",
            f"prompt_hash   : {self.prompt_hash}",
            f"corpus_hash   : {self.corpus_hash}",
            f"harness_sha   : {self.harness_sha}",
            f"config_hash   : {self.config_hash}",
            f"client_region : {self.client_region or '(미기록)'}",
            f"created_at    : {self.created_at.isoformat()}",
            f"params_sent   : {json.dumps(self.params_sent, sort_keys=True, ensure_ascii=False)}",
            f"params_omitted: {', '.join(self.params_omitted) or '(없음)'}",
            "tools         : "
            + (", ".join(f"{t.name}=={t.version}" for t in self.tool_versions) or "(없음)"),
        ]
        return "\n".join(lines)
