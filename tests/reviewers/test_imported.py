"""가져온 지적 - 미측정이 미탐지로 둔갑하지 않게."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.reviewers.imported import ImportedReviewer

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
