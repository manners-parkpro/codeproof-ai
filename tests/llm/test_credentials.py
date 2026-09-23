"""자격증명 확인.

🔴 이 모듈이 하는 일은 **정확히 말하는 것**뿐이다 - 인증을 구현하지 않는다.
   SDK 가 이미 환경변수 → OAuth 프로필 순으로 해결하므로,
   여기서 틀린 안내를 하면 사용자가 잘못된 곳을 고치게 된다.

[실측] 처음엔 "OpenAI 는 OAuth 경로 없음" 이라고 단정했는데 틀렸다 -
       Codex CLI 로그인은 존재한다. 다만 SDK 가 그 파일을 읽지 않고,
       auth.json 의 OPENAI_API_KEY 는 null 이며 구독 OAuth 토큰만 있다.
       그 차이를 안내가 정확히 말해야 한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from codeproof_ai.llm import credentials as cred
from codeproof_ai.llm.credentials import Source, all_statuses


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


class TestAnthropicResolution:
    def test_api_key_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
        st = cred.anthropic_status()
        assert st.ready
        assert st.source is Source.ENV_KEY

    def test_auth_token_is_second(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
        assert cred.anthropic_status().source is Source.ENV_TOKEN

    def test_oauth_profile_is_third(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "profile.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(cred, "_ANTHROPIC_PROFILE_DIR", tmp_path)
        st = cred.anthropic_status()
        assert st.ready
        assert st.source is Source.OAUTH_PROFILE

    def test_empty_profile_dir_is_not_credentials(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cred, "_ANTHROPIC_PROFILE_DIR", tmp_path)
        assert not cred.anthropic_status().ready

    def test_missing_gives_actionable_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cred, "_ANTHROPIC_PROFILE_DIR", tmp_path / "nope")
        detail = cred.anthropic_status().detail
        assert "console.anthropic.com" in detail or "ant auth login" in detail


class TestOpenAIResolution:
    def test_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
        assert cred.openai_status().ready

    def test_codex_login_is_reported_but_not_usable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """🔴 로그인이 있는데 안 되는 이유를 정확히 말해야 한다.

        "자격증명 없음" 으로만 말하면 사용자가 이미 한 로그인을 또 한다.
        """
        auth = tmp_path / "auth.json"
        auth.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(cred, "_CODEX_AUTH", auth)

        st = cred.openai_status()
        assert not st.ready
        assert "Codex CLI" in st.detail
        assert "API 키가 아니다" in st.detail

    def test_without_codex_login_the_hint_is_plain(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cred, "_CODEX_AUTH", tmp_path / "nope.json")
        st = cred.openai_status()
        assert "Codex CLI" not in st.detail
        assert "platform.openai.com" in st.detail


class TestAllStatuses:
    def test_covers_both_providers(self) -> None:
        assert {s.provider for s in all_statuses()} == {"anthropic", "openai"}

    def test_never_leaks_secret_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """🔴 상태 보고에 키 값이 섞이면 로그·스크린샷으로 샌다."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SECRET-VALUE")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-oai-SECRET-VALUE")
        for st in all_statuses():
            assert "SECRET" not in st.detail
            assert "SECRET" not in st.source.value
