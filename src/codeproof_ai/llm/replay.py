"""결정적 대체 provider - 자격증명 없이 파이프라인을 끝까지 돌린다.

버리는 코드가 아니다. 이후로도 계속 쓴다:
  - 파이프라인 회귀 테스트 (돈도 네트워크도 없이)
  - 실제 호출 전 드라이런
  - 기록된 응답을 되돌려 **과거 실행을 정확히 재현** (F8 의 아카이브가 살아나는 지점)

🔴 이 provider 의 숫자를 결과로 보고하지 않는다. 배관 검증 전용이다.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from codeproof_ai.llm.base import ReviewResponse, TokenUsage
from codeproof_ai.llm.parse import parse_findings

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.domain.target import ReviewTarget


class ReplayProvider:
    """기록된 응답을 되돌려주거나, 없으면 결정적으로 합성한다.

    Args:
        recordings: 기록 디렉터리. `<target_id>.<run>.json` 을 찾는다.
        synth_rate: 기록이 없을 때 지적을 만들어낼 확률(0~1)을 결정하는 기준.
            해시 기반이라 같은 입력에 항상 같은 결과가 나온다.
    """

    name = "replay"

    def __init__(
        self,
        model_id: str = "replay-v1",
        recordings: Path | None = None,
        synth_rate: float = 0.5,
    ) -> None:
        self.model_id = model_id
        self.recordings = recordings
        if not 0.0 <= synth_rate <= 1.0:
            msg = f"synth_rate 는 [0,1] 이다: {synth_rate}"
            raise ValueError(msg)
        self.synth_rate = synth_rate
        self._run = 0

    def review(
        self,
        target: ReviewTarget,
        *,
        effort: str,
        cache_nonce: str | None = None,
        stream: bool = False,  # noqa: ARG002 - Protocol 시그니처 유지. 재생에는 무의미
    ) -> ReviewResponse:
        run = self._run
        self._run += 1

        payload = self._recorded(target.target_id, run)
        replayed = payload is not None
        if payload is None:
            payload = self._synthesize(target, run, effort)

        parsed = parse_findings(payload, source=self.name, target=target)
        body = json.dumps(payload, ensure_ascii=False)

        return ReviewResponse(
            findings=parsed.findings,
            usage=TokenUsage(
                total_input=len(body) // 4,
                output=len(body) // 4,
            ),
            raw={
                "replayed": replayed,
                "run": run,
                "effort": effort,
                "nonce": cache_nonce,
                "payload": payload,
                "rejected": list(parsed.rejected),
            },
            wire_schema={},
            request_id=f"replay-{target.target_id}-{run}",
            ttft_ms=None,
            total_ms=None,
        )

    def _recorded(self, target_id: str, run: int) -> dict[str, Any] | None:
        if self.recordings is None:
            return None
        path = self.recordings / f"{target_id}.{run}.json"
        if not path.is_file():
            return None
        loaded: Any = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else None

    def _synthesize(
        self, target: ReviewTarget, run: int, effort: str
    ) -> dict[str, Any]:
        """입력 해시로 결정적으로 지적을 만든다.

        같은 (대상, 실행번호) 에는 항상 같은 결과가 나오므로
        다회 샘플링 · 그룹핑 · 임계값 로직을 실제로 시험할 수 있다.
        """
        seed = hashlib.blake2b(
            f"{target.target_id}|{run}|{effort}".encode(), digest_size=8
        ).digest()
        draw = seed[0] / 255.0
        if draw > self.synth_rate:
            return {"findings": []}

        first = target.files[0]
        lines = first.content.splitlines() or [""]
        # 비어 있지 않은 줄 하나를 고른다 - 인용문이 실제로 존재해야 한다.
        candidates = [i for i, ln in enumerate(lines, start=1) if ln.strip()]
        if not candidates:
            return {"findings": []}
        line = candidates[seed[1] % len(candidates)]

        return {
            "findings": [
                {
                    "file": first.path,
                    "line_start": line,
                    "line_end": line,
                    "category": "correctness",
                    "severity": "warning",
                    "quoted_code": lines[line - 1],
                    "message": f"[replay] synthetic finding at line {line}",
                    "failure_mode": "[replay] 합성된 지적 - 결과로 보고하지 않는다",
                }
            ]
        }
