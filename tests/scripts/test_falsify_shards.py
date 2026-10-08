"""falsify 조각 - CI 가 가드를 나눠 돌아도 빠지거나 겹치는 시나리오가 없다 (H3).

조각이 시나리오를 빠뜨리면 그 가드는 CI 에서 아무도 깨뜨려 보지 않는데,
요약 줄은 여전히 「다 울었다」다.
`--list` 는 트리를 고치지 않으므로 하네스를 그대로 부른다.
"""

from __future__ import annotations

import itertools
import os
import subprocess
from pathlib import Path

import pytest

FALSIFY = Path(__file__).resolve().parents[2] / "scripts" / "falsify.sh"


def _list(shard: str | None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "FALSIFY_SHARD"}
    if shard is not None:
        env["FALSIFY_SHARD"] = shard
    return subprocess.run(
        ["bash", str(FALSIFY), "--list"],
        capture_output=True, text=True, env=env, timeout=60, check=False,
    )


def _names(r: subprocess.CompletedProcess[str]) -> list[str]:
    assert r.returncode == 0, r.stderr
    return [line.split()[0] for line in r.stdout.splitlines() if line.strip()]


@pytest.mark.parametrize("n", [2, 3])
def test_shards_cover_every_scenario_exactly_once(n: int) -> None:
    everything = _names(_list(None))
    parts = [_names(_list(f"{k}/{n}")) for k in range(1, n + 1)]
    assert all(parts), "빈 조각은 「다 울었다」로 읽힌다"
    assert sorted(itertools.chain.from_iterable(parts)) == sorted(everything), "빠지거나 겹쳤다"


@pytest.mark.parametrize("bad", ["0/2", "3/2", "1", "a/b", "1/0", "-1/2", "999/999"])
def test_a_malformed_or_empty_shard_is_refused(bad: str) -> None:
    r = _list(bad)
    assert r.returncode == 2
    assert "FALSIFY_SHARD" in r.stderr
