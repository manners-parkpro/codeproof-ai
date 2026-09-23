"""일괄 분석 - 속도는 정확성을 바꾸지 않아야 한다.

🔴 이 모듈의 핵심 단언: **일괄과 개별이 같은 결과를 낸다.**
   다르면 같은 코퍼스에 두 개의 숫자가 생긴다.

[실측] 이 단언을 세우는 과정에서 두 가지 실제 결함이 드러났다:
  ① `__init__.py` 를 무조건 넣었더니 Ruff 의 INP001 이 사라졌다
     -> 복원 방식이 분석 결과를 바꾸면 안 된다 (as_packages 로 분리)
  ② mypy 가 호스트 프로젝트의 pyproject.toml `strict = true` 를 주워왔다
     -> --config-file=/dev/null 로 격리 (Ruff 의 --isolated 대응물)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codeproof_ai.analysis.base import materialize_many, split_batch_path
from codeproof_ai.analysis.python.mypy_ import MypyAnalyzer
from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.analysis.toolchain import ToolNotFoundError, resolve
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.loader import load_decoy_samples

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _key(findings: object) -> list[tuple[str, str, int]]:
    return sorted(
        (f.rule_id, f.location.path, f.location.line)
        for f in findings  # type: ignore[attr-defined]
    )


class TestBatchEqualsIndividual:
    """🔴 속도 최적화가 숫자를 바꾸면 그건 최적화가 아니라 버그다."""

    # 동치는 **성질**이라 코퍼스 전체가 필요하지 않다. 개별 경로는 대상마다
    # subprocess 를 띄우므로(mypy 는 대상당 ~0.5s) 표본을 쓴다.
    # 지적이 나오는 대상을 반드시 포함시켜야 「둘 다 0건」으로 통과하지 않는다.
    SAMPLE_IDS = (
        "D002-shell-true-constant-command",       # ruff S602 · bandit B602
        "D002-shell-true-constant-command#twin",
        "D012-isinstance-narrowed#twin",          # mypy union-attr
        "D009-unreachable-legacy-branch",         # 분기 관련
    )

    def _targets(self) -> list[ReviewTarget]:
        by_id = {s.sample_id: s.target for s in load_decoy_samples(DECOYS)}
        missing = [i for i in self.SAMPLE_IDS if i not in by_id]
        assert not missing, f"표본이 코퍼스에서 사라졌다: {missing}"
        return [by_id[i] for i in self.SAMPLE_IDS]

    @pytest.mark.parametrize(
        "analyzer",
        [RuffAnalyzer(select=("ALL",)), MypyAnalyzer()],
        ids=["ruff", "mypy"],
    )
    def test_same_findings(self, analyzer: RuffAnalyzer | MypyAnalyzer) -> None:
        targets = self._targets()
        one = {t.target_id: analyzer.analyze(t) for t in targets}
        many = analyzer.analyze_many(targets)

        assert set(one) == set(many)
        for tid, findings in one.items():
            assert _key(findings) == _key(many[tid]), f"{tid} 에서 갈린다"

    def test_the_sample_actually_produces_findings(self) -> None:
        """🔴 표본에 지적이 없으면 동치 검증이 「둘 다 0건」으로 공허하게 통과한다."""
        targets = self._targets()
        total = sum(
            len(fs)
            for a in (RuffAnalyzer(select=("ALL",)), MypyAnalyzer())
            for fs in a.analyze_many(targets).values()
        )
        assert total > 0, "표본이 아무 지적도 내지 않는다 - 동치 검증이 무의미하다"

    def test_empty_input(self) -> None:
        assert RuffAnalyzer().analyze_many([]) == {}
        assert MypyAnalyzer().analyze_many([]) == {}


class TestMaterializeMany:
    def test_boxes_are_isolated(self) -> None:
        """같은 파일명이 여러 대상에 있어도 겹치지 않아야 한다."""
        targets = [
            ReviewTarget(target_id=f"t{i}", files=(SourceFile("decoy.py", f"x = {i}\n"),))
            for i in range(3)
        ]
        with materialize_many(targets) as (root, mapping):
            boxes = sorted(p.name for p in root.iterdir())
            assert len(boxes) == 3
            assert set(mapping.values()) == {"t0", "t1", "t2"}
            for slug, tid in mapping.items():
                content = (root / slug / "decoy.py").read_text(encoding="utf-8")
                assert content == f"x = {tid[1:]}\n"

    def test_slugs_are_valid_identifiers(self) -> None:
        """🔴 sample_id 에 하이픈과 # 이 있으면 모듈명이 될 수 없다."""
        targets = [
            ReviewTarget(
                target_id="D001-some-name#twin",
                files=(SourceFile("a.py", "x = 1\n"),),
            )
        ]
        with materialize_many(targets) as (_root, mapping):
            for slug in mapping:
                assert slug.isidentifier(), f"{slug} 은 유효한 식별자가 아니다"

    def test_packages_are_opt_in(self) -> None:
        """🔴 복원 방식이 분석 결과를 바꾸면 안 된다.

        [실측] __init__.py 를 무조건 넣었더니 Ruff 의 INP001 이 사라졌다.
        mypy 만 필요로 하므로 선택적이어야 한다.
        """
        targets = [
            ReviewTarget(target_id="t", files=(SourceFile("a.py", "x = 1\n"),))
        ]
        with materialize_many(targets) as (root, mapping):
            slug = next(iter(mapping))
            assert not (root / slug / "__init__.py").exists()

        with materialize_many(targets, as_packages=True) as (root, mapping):
            slug = next(iter(mapping))
            assert (root / slug / "__init__.py").is_file()

    def test_cleanup(self) -> None:
        targets = [ReviewTarget(target_id="t", files=(SourceFile("a.py", "1\n"),))]
        with materialize_many(targets) as (root, _):
            saved = root
        assert not saved.exists()


class TestSplitBatchPath:
    def test_splits_slug_and_relative(self, tmp_path: Path) -> None:
        got = split_batch_path(tmp_path, str(tmp_path / "s0001" / "pkg" / "a.py"))
        assert got == ("s0001", "pkg/a.py")

    def test_outside_root_is_none(self, tmp_path: Path) -> None:
        assert split_batch_path(tmp_path, "/elsewhere/a.py") is None

    def test_root_level_file_is_none(self, tmp_path: Path) -> None:
        assert split_batch_path(tmp_path, str(tmp_path / "a.py")) is None


class TestToolchain:
    """[실측] uv run 오버헤드: ruff 53->10ms, mypy 308->123ms."""

    def test_resolves_to_direct_binary_when_on_path(self) -> None:
        cmd = resolve("ruff")
        assert len(cmd) == 1, f"uv run 을 거치고 있다: {cmd}"
        assert cmd[0].endswith("ruff")

    def test_unknown_tool_falls_back_to_uv(self) -> None:
        """PATH 에 없으면 uv run 으로 되돌아간다 - venv 밖에서 쓰일 수 있다."""
        cmd = resolve("this-tool-does-not-exist-xyz")
        assert cmd[:2] == ["uv", "run"]

    def test_raises_when_nothing_is_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "codeproof_ai.analysis.toolchain.shutil.which", lambda _t: None
        )
        with pytest.raises(ToolNotFoundError, match="찾을 수 없다"):
            resolve("ruff")


class TestHostConfigIsolation:
    """🔴 측정 도구가 호스트 레포 설정을 주워오면 재현성이 무너진다."""

    def test_mypy_blocks_project_config(self) -> None:
        """[실측] 없으면 이 레포의 strict=true 를 주워와 다른 숫자를 낸다."""
        assert "--config-file=/dev/null" in MypyAnalyzer.DEFAULT_FLAGS

    def test_mypy_blocks_incremental_cache(self) -> None:
        """🔴 [실측] 캐시가 살아 있으면 **삭제된 임시 디렉터리 경로**의 진단이
        섞여 나온다 - 재현성 이전에 정확성 문제다."""
        assert "--no-incremental" in MypyAnalyzer.DEFAULT_FLAGS
        assert "--cache-dir=/dev/null" in MypyAnalyzer.DEFAULT_FLAGS

    def test_isolation_is_recorded_in_signature(self) -> None:
        """매니페스트가 거짓을 기록하지 않아야 한다."""
        sig = MypyAnalyzer().config_signature()
        assert "isolated" in sig
        assert "no-cache" in sig

    def test_ruff_uses_isolated(self) -> None:
        targets = [
            ReviewTarget(target_id="t", files=(SourceFile("a.py", "import os\n"),))
        ]
        # --isolated 가 없으면 이 레포의 extend-exclude 등이 적용될 수 있다
        findings = RuffAnalyzer(select=("F",)).analyze_many(targets)["t"]
        assert any(f.rule_id == "F401" for f in findings)
