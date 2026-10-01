"""가져온 지적 - 미측정이 미탐지로 둔갑하지 않게."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.reviewers.imported import (
    BUNDLE_FILE,
    RUN_FILE,
    ImportedReviewer,
    pack_runs,
    unpack_runs,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, name: str) -> None:
    (root / name).write_text(json.dumps({"findings": []}), encoding="utf-8")


def _reviewer(root: Path) -> ImportedReviewer:
    return ImportedReviewer(root, name="a", identity="t", kind=ReviewerKind.AGENT, fmt="native")


class TestAvailableRuns:
    def test_contiguous_runs_are_counted(self, tmp_path: Path) -> None:
        for i in range(3):
            _write(tmp_path, f"S.{i}.json")
        assert _reviewer(tmp_path).available_runs("S") == 3

    def test_a_gap_stops_the_count(self, tmp_path: Path) -> None:
        """🔴 실패한 회차가 비면 개수는 맞아 보여도 review() 는 그 회차를 「지적 0건」으로 낸다."""
        for i in (0, 1, 2, 4):
            _write(tmp_path, f"S.{i}.json")
        assert _reviewer(tmp_path).available_runs("S") == 3

    def test_other_samples_do_not_count(self, tmp_path: Path) -> None:
        # `S` 의 회차를 세는데 `S#twin` 파일이 끼면 안 된다.
        _write(tmp_path, "S.0.json")
        _write(tmp_path, "S#twin.0.json")
        _write(tmp_path, "S#twin.1.json")
        assert _reviewer(tmp_path).available_runs("S") == 1

    def test_single_file_layout(self, tmp_path: Path) -> None:
        _write(tmp_path, "S.json")
        assert _reviewer(tmp_path).available_runs("S") == 1


class TestBundle:
    """저장소에 싣는 묶음 - 풀면 실행기 출력과 **같아야** 같은 경로로 재생된다."""

    def _runner_output(self, root: Path) -> Path:
        src = root / "src"
        src.mkdir()
        for name, n in (("D1", 2), ("D1#twin", 2), ("D10", 1)):
            for i in range(n):
                finding = {"message": f"{name}/{i}", "line_start": i + 1}
                (src / f"{name}.{i}.json").write_text(
                    json.dumps({"findings": [finding]}), encoding="utf-8"
                )
        (src / RUN_FILE).write_text("{}", encoding="utf-8")
        return src

    def test_unpack_restores_every_run(self, tmp_path: Path) -> None:
        src = self._runner_output(tmp_path)
        bundle = tmp_path / BUNDLE_FILE
        bundle.write_text(pack_runs(src), encoding="utf-8")
        dest = tmp_path / "dest"
        dest.mkdir()
        unpack_runs(bundle, dest)

        def runs(d: Path) -> dict[str, object]:
            return {p.name: json.loads(p.read_text()) for p in d.glob("*.*.json")}

        assert runs(dest) == runs(src)
        assert len(runs(dest)) == 5, "샘플 이름의 `#` · 두 자리 회차도 되살아나야 한다"
        assert not (dest / RUN_FILE).exists(), "실행 기록은 회차가 아니다 - 따로 옮긴다"

    def test_packing_is_deterministic(self, tmp_path: Path) -> None:
        """같은 출력은 같은 바이트 - 아니면 커밋 diff 가 실제 변화를 가린다."""
        src = self._runner_output(tmp_path)
        assert pack_runs(src) == pack_runs(src)
        ids = [json.loads(line)["sample_id"] for line in pack_runs(src).splitlines()]
        assert ids == sorted(ids)


class TestConfigSignature:
    """🔴 실행을 가르는 RUN.json 항목은 설정 지문에 싣는다 (F1).

    빠지면 다른 실행이 같은 설정으로 읽힌다.
    """

    def _signature(self, root: Path, run: dict[str, str]) -> str:
        root.mkdir()
        (root / RUN_FILE).write_text(json.dumps(run), encoding="utf-8")
        return _reviewer(root).config_signature()

    def test_runner_version_changes_the_signature(self, tmp_path: Path) -> None:
        """[실측] runner_version 이 빠져 있어서 2 → 3 으로 바꿔도 config_hash 가 같았다."""
        run = {"runner_version": "2", "model": "m-1", "effort": "low"}
        first = self._signature(tmp_path / "a", run)
        again = self._signature(tmp_path / "b", dict(run))
        bumped = self._signature(tmp_path / "c", {**run, "runner_version": "3"})
        assert first == again, "같은 실행 기록이 다른 설정으로 읽혔다"
        assert first != bumped, "실행기 판이 달라도 같은 설정으로 읽힌다"

    def test_docstring_knob_changes_the_signature(self, tmp_path: Path) -> None:
        """🔴 프롬프트 해시가 같아도 입력 코드가 다르다 - keep 과 neutral 이 한 설정으로 읽히면
        손잡이 효과를 잴 수 없다 (DESIGN §7.10c)."""
        run = {"runner_version": "3", "model": "m-1", "effort": "low", "docstrings": "keep"}
        keep = self._signature(tmp_path / "a", run)
        again = self._signature(tmp_path / "b", dict(run))
        neutral = self._signature(tmp_path / "c", {**run, "docstrings": "neutral"})
        assert keep == again, "같은 실행 기록이 다른 설정으로 읽혔다"
        assert keep != neutral, "docstring 손잡이가 달라도 같은 설정으로 읽힌다"
