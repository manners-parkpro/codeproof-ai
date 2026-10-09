"""작성 기록 공개 도구 (DESIGN §7.10d 「공개」) - 가리기 · 훑기 · 묶기를 가짜 기록으로 본다.

🔴 push 는 되돌릴 수 없다 - 가리기가 빠지거나 훑기가 공허하면 로컬 경로 · 토큰이 공개 이력에 남는다.
   우는 입력은 실행 중에 만든다 - 토큰처럼 보이는 글을 시험 파일에 그대로 두지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "xauthor_publish.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("xauthor_publish", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


xp = _load()
FAKE_KEY = "sk-" + "a1B2" * 6
FAKE_MAIL = "someone" + "@" + "company" + ".io"


def _root(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "stage9"
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


class TestMask:
    def test_machine_paths_are_masked(self) -> None:
        text = (
            f"{xp.REPO}/runs/x {Path.home()}/.codex /Users/Shared/xauthor-venv-run/bin/python "
            "/private/var/folders/ab/cd/T/tmpx/repro.py"
        )
        got = xp.mask(text)
        assert got == "<repo>/runs/x ~/.codex <shared>/xauthor-venv-run/bin/python <tmp>"
        assert str(Path.home()) not in got

    def test_a_homebrew_python_path_is_not_an_email(self) -> None:
        line = "/opt/homebrew/Cellar/python@3.14/3.14.6/Frameworks/x.py"
        assert not xp.SECRETS["이메일"].search(line)

    @pytest.mark.parametrize("mail", ["ops@example.com", "a@b.test"])
    def test_example_addresses_are_not_secrets(self, mail: str) -> None:
        assert not xp.SECRETS["이메일"].search(mail)


class TestPublish:
    def test_a_clean_record_is_bundled_masked_and_in_path_order(self, tmp_path: Path) -> None:
        root = _root(tmp_path, {
            "XC002/write-1.err": f"cd {xp.REPO}/runs\n",
            "XC001/audit.json": '{"findings": []}\n',
            "XC001/final/XC001-x/__pycache__/decoy.pyc": "",
            ".lock": "",
        })
        out = tmp_path / "out"
        assert xp.publish([root], out) == []
        rows = [json.loads(ln) for ln in (out / "stage9.jsonl").read_text().splitlines()]
        assert [r["path"] for r in rows] == ["XC001/audit.json", "XC002/write-1.err"]
        assert rows[1]["text"] == "cd <repo>/runs\n"

    def test_the_same_record_gives_the_same_bytes(self, tmp_path: Path) -> None:
        root = _root(tmp_path, {"XC001/a.txt": "x\n", "XC001/b.txt": "y\n"})
        first, second = tmp_path / "1", tmp_path / "2"
        xp.publish([root], first)
        xp.publish([root], second)
        assert (first / "stage9.jsonl").read_bytes() == (second / "stage9.jsonl").read_bytes()

    @pytest.mark.parametrize(("text", "kind"), [
        (f"key={FAKE_KEY}", "API 키 (sk-)"),
        (f"mail {FAKE_MAIL}", "이메일"),
        ('{"refresh_token": "x"}', "인증 필드"),
    ])
    def test_a_secret_stops_everything_and_is_not_printed(
        self, tmp_path: Path, text: str, kind: str
    ) -> None:
        """🔴 하나라도 보이면 아무것도 쓰지 않는다 - 보고에는 자리와 종류만 싣는다."""
        root = _root(tmp_path, {"XC001/clean.txt": "ok\n", "XC002/write-1.jsonl": f"a\n{text}\n"})
        out = tmp_path / "out"
        found = xp.publish([root], out)
        assert found == [f"stage9/XC002/write-1.jsonl:2 · {kind}"]
        assert not out.exists()
        assert not any(text in f for f in found)

    def test_check_writes_nothing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        root = _root(tmp_path, {"XC001/a.txt": "x\n"})
        assert xp.main(["--check", str(root)]) == 0
        assert "0건" in capsys.readouterr().out
        assert [p.name for p in tmp_path.iterdir()] == ["stage9"]
