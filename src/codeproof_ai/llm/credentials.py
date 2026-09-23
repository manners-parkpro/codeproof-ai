"""자격증명 확인 - 무엇이 있고 무엇이 없는지 정확히 말한다.

🔴 인증을 직접 구현하지 않는다. SDK 가 이미 환경변수 -> OAuth 프로필 순으로
   해결하므로, 어느 경로로 로그인하든 어댑터 코드는 그대로다.
   여기서는 **무엇이 잡히는지 보고**만 한다.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Source(StrEnum):
    ENV_KEY = "env:API_KEY"
    ENV_TOKEN = "env:AUTH_TOKEN"  # noqa: S105 - 값이 아니라 출처 이름이다
    OAUTH_PROFILE = "oauth-profile"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Status:
    provider: str
    source: Source
    detail: str

    @property
    def ready(self) -> bool:
        return self.source is not Source.NONE


_ANTHROPIC_PROFILE_DIR = Path.home() / ".config" / "anthropic"


def anthropic_status() -> Status:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return Status("anthropic", Source.ENV_KEY, "ANTHROPIC_API_KEY 설정됨")
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return Status("anthropic", Source.ENV_TOKEN, "ANTHROPIC_AUTH_TOKEN 설정됨")
    if _ANTHROPIC_PROFILE_DIR.is_dir() and any(_ANTHROPIC_PROFILE_DIR.iterdir()):
        return Status(
            "anthropic",
            Source.OAUTH_PROFILE,
            f"OAuth 프로필 있음 ({_ANTHROPIC_PROFILE_DIR})",
        )
    # ⚠ Claude Code / claude.ai 구독 로그인은 여기에 해당하지 않는다.
    #   대화형 도구용 인증이지 SDK 가 읽는 자격증명이 아니다.
    #   `ant auth login` 이 만드는 프로필은 SDK 가 읽는다 - 그건 다른 물건이다.
    has_cli = shutil.which("ant") is not None
    hint = (
        "`ant auth login` 으로 프로필을 만든다"
        if has_cli
        else "console.anthropic.com 에서 API 키를 발급받는다 (`ant` CLI 미설치)"
    )
    return Status("anthropic", Source.NONE, f"자격증명 없음 - {hint}")


_CODEX_AUTH = Path.home() / ".codex" / "auth.json"


def _codex_login_present() -> bool:
    """Codex CLI 가 로그인돼 있는가.

    🔴 있어도 SDK 는 쓸 수 없다 - 아래 주석 참조. 그래도 확인하는 이유는
       「로그인했는데 왜 안 되냐」는 질문에 정확히 답하기 위해서다.
    """
    return _CODEX_AUTH.is_file()


def openai_status() -> Status:
    if os.environ.get("OPENAI_API_KEY"):
        return Status("openai", Source.ENV_KEY, "OPENAI_API_KEY 설정됨")

    # Codex CLI 로그인이 있어도 이 벤치마크는 돌지 않는다:
    #   1. openai SDK 는 OPENAI_API_KEY 환경변수만 읽는다.
    #      ~/.codex/auth.json 을 알지 못한다.
    #   2. 그 파일의 OPENAI_API_KEY 는 null 이고 ChatGPT 구독 OAuth 토큰만 있다.
    #      JWT 는 sk-... 키가 아니라 형식이 다르다.
    #   3. 설령 된다 해도 그건 **Codex CLI(에이전트)** 를 재는 것이지
    #      모델 API 를 재는 게 아니다 - 비교 축이 달라진다.
    if _codex_login_present():
        return Status(
            "openai",
            Source.NONE,
            "Codex CLI 로그인은 있으나 SDK 가 쓸 수 없다 "
            "(구독 OAuth 토큰이지 API 키가 아니다) - platform.openai.com 에서 키 발급 필요",
        )
    return Status(
        "openai",
        Source.NONE,
        "자격증명 없음 - platform.openai.com 에서 API 키를 발급받는다",
    )


def all_statuses() -> tuple[Status, ...]:
    return (anthropic_status(), openai_status())
