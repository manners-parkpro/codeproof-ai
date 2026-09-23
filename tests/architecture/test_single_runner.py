"""실행 경로가 하나인지 강제한다.

🔴 왜 이 테스트가 있는가.

전에 run_analyzer · run_provider · run_reviewer 셋이 같은 단계(관측 -> 채점)를
각자 구현했다. 짝 채점자를 위해 `bind_run` 훅을 추가할 때 run_reviewer 에만
걸었고, 나머지 둘은 **조용히 빈 짝을 보고 전부 TP** 로 채점했다. 예외도 경고도
없었다. CLI 의 measure 명령이 그 경로를 쓰고 있었으므로 production 버그였다.

경로가 하나면 이 실수가 구조적으로 불가능해진다. 그래서 테스트로 고정한다.
"""

from __future__ import annotations

import inspect

import pytest

from codeproof_ai.analysis.registry import create_analyzer
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval import runner
from codeproof_ai.eval.grading.base import UnboundGraderError
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.sample import LabeledSample, Stratum
from codeproof_ai.llm.registry import create_provider
from codeproof_ai.reviewers.wrap import AnalyzerReviewer, ProviderReviewer


class TestOneEntryPoint:
    def test_only_one_public_run_function(self) -> None:
        public_runs = sorted(
            n
            for n, obj in vars(runner).items()
            if n.startswith("run") and inspect.isfunction(obj)
        )
        assert public_runs == ["run_reviewer"], (
            f"실행 경로가 여럿이다: {public_runs}. "
            "경로가 갈리면 새 훅이 한쪽에만 걸린다 - 실제로 그래서 짝 채점이 틀렸다."
        )

    def test_runner_binds_before_grading(self) -> None:
        """관측이 끝난 뒤에 채점한다 - 소스 순서로 확인한다."""
        src = inspect.getsource(runner.run_reviewer)
        assert src.index("_bind_run_context") < src.index("_grade(s, obs"), (
            "채점보다 먼저 bind 해야 한다 - 짝의 지적이 아직 없는 채로 채점된다."
        )


class TestUnboundGraderIsLoud:
    """🔴 문맥 없이 돌면 조용히 틀리는 대신 터진다."""

    def test_judging_without_bind_raises(self) -> None:
        g = PairedFixGrader()
        with pytest.raises(UnboundGraderError, match="bind_run"):
            g.judge(_dummy_sample(), [])

    def test_bound_grader_judges(self) -> None:
        g = PairedFixGrader()
        g.bind_run({})
        assert g.judge(_dummy_sample(), []) == []


def _dummy_sample() -> LabeledSample:
    return LabeledSample(
        target=ReviewTarget(
            target_id="x", files=(SourceFile(path="a.py", content="x = 1\n"),)
        ),
        stratum=Stratum.CLEAN_PR,
    )


class TestManifestIsNotGuessed:
    """🔴 매니페스트 항목은 러너가 짐작하지 않고 리뷰어가 신고한다.

    러너를 하나로 합치면서 실제로 두 가지를 잃을 뻔했다:
      · 모델 리뷰어의 effort 가 "n/a" 로 기록됨 (거짓말)
      · 분석기의 도구 버전이 (없음) 으로 기록됨 (재현 불가)
    둘 다 **숫자는 그대로인데 출처를 잃는** 종류라 눈에 안 띈다. 그래서 고정한다.
    """

    def test_analyzer_reports_its_tool_version(self) -> None:

        r = AnalyzerReviewer(create_analyzer("ruff"))
        assert [t.name for t in r.tool_versions()] == ["ruff"]
        assert r.tool_versions()[0].version

    def test_model_reviewer_reports_effort_and_cache_policy(self) -> None:

        r = ProviderReviewer(
            create_provider("replay"), effort="high", cache_policy="nonce"
        )
        assert r.manifest_fields() == {
            "effort": "high",
            "cache_policy": "nonce",
        }

    def test_run_carries_the_declared_fields(self) -> None:

        run = run_reviewer(
            AnalyzerReviewer(create_analyzer("ruff")), [_dummy_sample()], []
        )
        assert run.manifest.tool_versions, "도구 버전이 매니페스트에서 사라졌다"
        assert run.manifest.effort == "n/a(static)"
