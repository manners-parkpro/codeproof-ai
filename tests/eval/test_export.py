"""에이전트용 내보내기 - 에이전트가 model_api 와 **같은 과제**를 받는가."""

from __future__ import annotations

import ast
import dataclasses
import json
import re
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.domain.target import SourceFile
from codeproof_ai.eval.export import (
    MANIFEST_FILE,
    PROMPT_FILE,
    SCHEMA_FILE,
    build_prompt,
    export_for_agent,
    neutral_docstring,
    sample_digest,
)
from codeproof_ai.eval.gate import neutral_problem
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.llm.render import load_prompt, prompt_hash
from codeproof_ai.llm.schema import review_schema
from tests.corpora import made_corpora

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.eval.sample import LabeledSample


def _required() -> list[str]:
    return list(review_schema()["properties"]["findings"]["items"]["required"])


def _contract_fields(prompt: str) -> list[str]:
    block = prompt.split("## Output", 1)[1]
    return re.findall(r'"(\w+)":', block.split("]}", 1)[0])


class TestContractMatchesModelApiSchema:
    """🔴 [실측] 손으로 적은 규격에서 `quoted_code`·`failure_mode` 가 빠져 있었다.

    인용이 없으면 LLM 지적의 지문이 (category, 파일) 로 수렴해 같은 파일의
    서로 다른 지적이 한 관측으로 뭉쳤다. 칸 하나하나를 적는 대신
    **스키마와 같은 집합인가**를 본다 - 칸이 늘어도 이 테스트는 낡지 않는다.
    """

    def test_every_schema_field_is_in_the_contract(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        fields = _contract_fields(build_prompt(shipped_samples))
        assert fields[0] == "findings"
        assert fields[1:] == _required()

    def test_the_fields_that_went_missing_are_there(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        # 위 테스트가 공허하지 않다는 확인 - 빠졌던 두 칸을 이름으로 본다.
        fields = _contract_fields(build_prompt(shipped_samples))
        assert "quoted_code" in fields
        assert "failure_mode" in fields

    def test_enums_come_from_the_schema_not_the_domain(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        # 도메인 Severity 에는 fatal 이 있지만 model_api 스키마에는 없다.
        # 에이전트에게 더 넓은 집합을 주면 과제가 달라진다.
        props = review_schema()["properties"]["findings"]["items"]["properties"]
        prompt = build_prompt(shipped_samples)
        assert f"severity: {' | '.join(props['severity']['enum'])}\n" in prompt
        assert f"category: {' | '.join(props['category']['enum'])}\n" in prompt

    def test_instruction_is_the_model_api_instruction(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        assert build_prompt(shipped_samples).startswith(load_prompt("review_v1"))


class TestFilesListedBelow:
    """지시가 "every file listed below" 라고 하므로 실제로 나열해야 한다."""

    def test_presented_files_are_listed(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        prompt = build_prompt(shipped_samples)
        section = prompt.split("## Files", 1)[1].split("## Output", 1)[0]
        for f in shipped_samples[0].target.files:
            assert f"- {f.path}\n" in section

    def test_rejects_samples_with_different_file_lists(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        a, b = shipped_samples[0], shipped_samples[1]
        other = dataclasses.replace(
            b,
            target=dataclasses.replace(
                b.target, files=(SourceFile(path="other.py", content="x = 1\n"),)
            ),
        )
        with pytest.raises(ValueError, match="제시 파일 목록"):
            build_prompt([a, other])


class TestExportedFiles:
    def test_schema_file_is_the_model_api_schema(
        self, shipped_samples: list[LabeledSample], tmp_path: Path
    ) -> None:
        export_for_agent(shipped_samples[:2], tmp_path)
        written = json.loads((tmp_path / SCHEMA_FILE).read_text(encoding="utf-8"))
        assert written == review_schema()

    def test_manifest_hashes(
        self, shipped_samples: list[LabeledSample], tmp_path: Path
    ) -> None:
        m = export_for_agent(shipped_samples[:2], tmp_path)
        on_disk = json.loads((tmp_path / MANIFEST_FILE).read_text(encoding="utf-8"))
        assert on_disk == m
        # 🔴 model_api 는 지시만 해싱한다 (cli: prompt_hash_of(load_prompt())).
        #    비교용 해시가 그것과 같아야 「같은 지시」라고 말할 수 있다.
        assert m["instruction_hash"] == prompt_hash(load_prompt("review_v1"))
        prompt = (tmp_path / PROMPT_FILE).read_text(encoding="utf-8")
        assert m["prompt_hash"] == prompt_hash(prompt)
        assert m["instruction_hash"] != m["prompt_hash"]

    def test_manifest_carries_each_samples_digest(
        self, shipped_samples: list[LabeledSample], tmp_path: Path
    ) -> None:
        """🔴 실행기가 회차마다 옮겨 적는 잰 코드의 지문 - pack 의 packed_digests 와 같은 함수다."""
        m = export_for_agent(shipped_samples[:2], tmp_path, docstrings="neutral")
        rows = m["samples"]
        assert isinstance(rows, list)
        assert [r["digest"] for r in rows] == [sample_digest(s) for s in shipped_samples[:2]]
        assert rows[0]["digest"] != rows[1]["digest"], "decoy 와 twin 은 코드가 다르다"


def _inner_docstrings(source: str) -> list[str | None]:
    return [
        ast.get_docstring(n)
        for n in ast.walk(ast.parse(source))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


class TestDocstringKnob:
    """🔴 [실측 · 60쌍] decoy 와 twin 이 안전 기전을 적은 같은 모듈 docstring 을 가졌다.

    twin 에서는 지켜지지 않는 약속이 되어 정답 단서가 된다 - 손잡이로 끄고 효과를 잰다
    (DESIGN §7.10c).
    """

    @pytest.mark.parametrize("root", made_corpora())
    def test_every_shipped_file_keeps_its_lines(self, root: Path) -> None:
        """줄 번호가 그대로여야 정답 구간(미끼 · 가드 · twin)이 맞는다 - 바뀌는 줄은 하나뿐이다.

        neutral 로 재는 코퍼스 전부를 본다 (DESIGN §7.10d 「수집 전에 준비할 것」 ②).
        """
        samples = load_decoy_samples(root)
        assert samples, f"{root} 에 쌍이 없다 - 대조가 공허하다"
        for s in samples:
            for f in s.target.files:
                assert neutral_problem(f.content) is None, s.sample_id  # 관문(§7.10d)과 같은 규칙

    def test_function_docstrings_are_untouched(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        """🔴 함수 · 클래스 docstring 은 그 자체가 가드일 수 있다 (D005 · D018 등)."""
        seen = 0
        for s in shipped_samples:
            for f in s.target.files:
                inner = _inner_docstrings(f.content)
                assert _inner_docstrings(neutral_docstring(f.content)) == inner, s.sample_id
                seen += sum(d is not None for d in inner)
        assert seen > 0, "대조군 - 함수 docstring 이 있는 샘플이 있어야 이 테스트가 뭔가를 본다"

    @pytest.mark.parametrize(
        "source",
        ["x = 1\n", '"""두 줄\n짜리 - 설명."""\n', '"""기전 없는 한 줄."""\n'],
        ids=["없음", "두 줄", "형식 아님"],
    )
    def test_rejects_what_it_cannot_neutralize(self, source: str) -> None:
        """조용히 원문을 내보내면 neutral 이라고 적힌 keep 이 된다."""
        with pytest.raises(ValueError, match="모듈 docstring"):
            neutral_docstring(source)

    def test_export_records_the_knob(
        self, shipped_samples: list[LabeledSample], tmp_path: Path
    ) -> None:
        keep = export_for_agent(shipped_samples[:2], tmp_path / "keep")
        neutral = export_for_agent(shipped_samples[:2], tmp_path / "neutral", docstrings="neutral")
        assert (keep["docstrings"], neutral["docstrings"]) == ("keep", "neutral")
        s = shipped_samples[0]
        f = s.target.files[0]
        kept = (tmp_path / "keep" / s.sample_id / f.path).read_text(encoding="utf-8")
        neutralized = (tmp_path / "neutral" / s.sample_id / f.path).read_text(encoding="utf-8")
        assert kept == f.content
        assert neutralized == neutral_docstring(f.content)
        assert neutralized != f.content

    def test_unknown_knob_is_rejected(
        self, shipped_samples: list[LabeledSample], tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="docstring 손잡이"):
            export_for_agent(shipped_samples[:1], tmp_path, docstrings="strip")
