"""하네스 자신의 버전을 매니페스트가 짐작하지 않는다.

🔴 `harness_sha` 가 기본값 `"uncommitted"` 로 고정돼 있었다. **방금 클론한
깨끗한 커밋 상태에서 돌려도** 그렇게 기록됐다 - 알 수 있는 것을 모른다고
적는 매니페스트다. 러너가 `effort="n/a"` 를 박아 넣던 것(E01)과 같은 종류다.

6개월 뒤 같은 `config_hash` 인데 결과가 다르면 「도구가 바뀌었나 하네스가
바뀌었나」를 물어야 한다. 하네스 쪽이 전부 `uncommitted` 면 답할 수 없다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codeproof_ai.analysis.registry import create_analyzer
from codeproof_ai.eval.provenance import DIRTY_SUFFIX, UNKNOWN, harness_sha
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.reviewers.wrap import AnalyzerReviewer


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


class TestItReportsTheRealSha:
    def test_clean_checkout_gives_a_bare_sha(self, repo: Path) -> None:
        sha = harness_sha(repo)
        assert sha != UNKNOWN
        assert not sha.endswith(DIRTY_SUFFIX)
        assert len(sha) == 12, f"짧은 SHA 가 아니다: {sha}"

    def test_uncommitted_changes_are_not_hidden(self, repo: Path) -> None:
        """🔴 더티 상태의 실행은 **재현할 수 없다.** 그 사실이 보여야 한다."""
        (repo / "a.txt").write_text("changed\n", encoding="utf-8")
        assert harness_sha(repo).endswith(DIRTY_SUFFIX)

    def test_untracked_files_count_as_dirty(self, repo: Path) -> None:
        (repo / "new.txt").write_text("y\n", encoding="utf-8")
        assert harness_sha(repo).endswith(DIRTY_SUFFIX)

    def test_a_non_repo_is_unknown_not_a_made_up_sha(self, tmp_path: Path) -> None:
        """거짓 SHA 를 지어내지 않는다 - 모르면 모른다고 적는다."""
        outside = Path(tmp_path, "nope")
        assert harness_sha(outside) == UNKNOWN


class TestTheRunnerUsesIt:
    def test_manifest_carries_a_real_sha_by_default(self) -> None:
        run = run_reviewer(AnalyzerReviewer(create_analyzer("ruff")), [], [])
        assert run.manifest.harness_sha != "uncommitted", (
            "매니페스트가 하네스 버전을 짐작하고 있다"
        )

    def test_an_explicit_value_still_wins(self) -> None:
        """테스트가 고정값을 줄 수 있어야 한다 - 안 그러면 스냅샷이 흔들린다."""
        run = run_reviewer(
            AnalyzerReviewer(create_analyzer("ruff")), [], [], harness_sha="pinned"
        )
        assert run.manifest.harness_sha == "pinned"
