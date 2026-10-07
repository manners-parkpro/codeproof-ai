"""리뷰 출력 스키마 - 양 벤더를 통과해야 한다.

🔴 평탄해야 한다 (CLAUDE.md D5).
   Anthropic 은 재귀 스키마를 지원하지 않고 OpenAI 는 지원한다.
   둘 다 통과하려면 낮은 쪽에 맞춘다.

Anthropic 미지원이라 쓰지 않는 것:
  재귀 · 외부 $ref · minimum/maximum/multipleOf ·
  minLength/maxLength · pattern · maxItems
  (minItems 는 0 또는 1 만 가능 - 여기서는 쓰지 않는다)

OpenAI strict 가 요구하는 것:
  additionalProperties: false · 모든 키가 required
  (선택 필드는 "type": ["string", "null"] 로 표현)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

CATEGORIES: Final = (
    "correctness",
    "security",
    "performance",
    "type_safety",
    "resource",
    "concurrency",
    "maintainability",
    "style",
    "other",
)

SEVERITIES: Final = ("info", "warning", "error")

SCHEMA_NAME: Final = "code_review"


def review_schema() -> dict[str, Any]:
    """양 벤더 공통 출력 스키마.

    🔴 findings 가 **빈 배열일 수 있어야 한다.**
       "지적 없음" 이 1급 답변이 아니면 모델이 뭐라도 만들어내고,
       그러면 측정된 FPR 은 모델 판단이 아니라 프롬프트 압력이 된다.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["findings"],
        "properties": {
            "findings": {
                "type": "array",
                "description": (
                    "발견한 문제들. 문제가 없으면 빈 배열을 반환한다 - "
                    "빈 배열은 완전히 정상적인 답변이다."
                ),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "file",
                        "line_start",
                        "line_end",
                        "category",
                        "severity",
                        "quoted_code",
                        "message",
                        "failure_mode",
                    ],
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "제시된 파일 경로 중 하나. 그대로 쓴다.",
                        },
                        "line_start": {
                            "type": "integer",
                            "description": "문제가 시작되는 줄 (1부터).",
                        },
                        "line_end": {
                            "type": "integer",
                            "description": "문제가 끝나는 줄 (1부터, 포함).",
                        },
                        "category": {"type": "string", "enum": list(CATEGORIES)},
                        "severity": {"type": "string", "enum": list(SEVERITIES)},
                        "quoted_code": {
                            "type": "string",
                            "description": (
                                "문제가 있는 코드를 **원문 그대로** 인용한다. "
                                "재작성하거나 요약하지 않는다. "
                                "제시된 파일에 이 문자열이 그대로 존재해야 한다."
                            ),
                        },
                        "message": {
                            "type": "string",
                            "description": "무엇이 문제인지 한두 문장.",
                        },
                        "failure_mode": {
                            "type": "string",
                            "description": (
                                "이 코드가 **구체적으로 어떻게** 실패하는지. "
                                "어떤 입력이나 상태에서 무엇이 잘못되는가. "
                                "실패 경로를 말할 수 없으면 지적하지 않는다."
                            ),
                        },
                    },
                },
            }
        },
    }


def _objects(node: object) -> Iterator[dict[str, Any]]:
    """스키마 안의 모든 객체(dict) - 아래 두 검사가 같은 순회를 쓴다."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from _objects(v)


def is_flat(schema: dict[str, Any]) -> bool:
    """재귀 참조가 없는지 - Anthropic 통과 조건."""
    return not any("$ref" in obj for obj in _objects(schema))


_BANNED_KEYWORDS: Final = frozenset(
    {"minimum", "maximum", "multipleOf", "minLength", "maxLength", "pattern", "maxItems"}
)


def unsupported_keywords(schema: dict[str, Any]) -> set[str]:
    """Anthropic 이 지원하지 않는 키워드가 섞였는지.

    SDK 가 조용히 제거하고 description 에 접어버리므로,
    보내기 전에 우리가 먼저 안다.
    """
    return {k for obj in _objects(schema) for k in _BANNED_KEYWORDS & obj.keys()}
