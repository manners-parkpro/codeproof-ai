"""작성 기록 공개 도구 (DESIGN §7.10d 「공개」) - 가리기 · 훑기 · 묶기를 가짜 기록으로 본다.

🔴 push 는 되돌릴 수 없다 - 가리기가 빠지거나 훑기가 공허하면 로컬 경로 · 토큰이 공개 이력에 남는다.
   우는 입력은 실행 중에 만든다 - 토큰처럼 보이는 글을 시험 파일에 그대로 두지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
FAKE_USER_ID = "user-" + "A1b2" * 6
FAKE_UUID = "1b2c3d4e-" + "5f6a-" * 3 + "7b8c9d0e1f2a"


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

    @pytest.mark.parametrize("mail", ["ops@example.com", "a@b.test", "Kim@Example.com"])
    def test_example_addresses_are_not_secrets(self, mail: str) -> None:
        assert not xp.SECRETS["이메일"].search(mail)

    def test_a_decorator_after_an_escaped_newline_is_not_an_email(self) -> None:
        """[실측 · D136 mutants.py] 문자열 안의 `\\n` 이 남긴 n 을 로컬 부분으로 읽었다."""
        code = "'_saved = None\\n\\n\\n@contextlib.contextmanager\\n'"
        assert not xp.SECRETS["이메일"].search(code)
        assert xp.SECRETS["이메일"].search(f"total 1\\n{FAKE_MAIL}"), "이스케이프 뒤의 진짜 주소"

    def test_the_account_name_is_masked(self) -> None:
        """🔴 [실측 · 2단계 기록 168곳] codex 가 돌린 ls -l 의 소유자 열 - 경로를 가려도 남는다."""
        line = f"drwxr-xr-x@  6 {xp.ACCOUNT.pw_name}  wheel  192 Oct  7 16:01 ."
        assert xp.mask(line) == "drwxr-xr-x@  6 <user>  wheel  192 Oct  7 16:01 ."

    def test_the_account_home_is_masked_whatever_home_says(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HOME 을 바꾼 셸에서 돌려도 계정의 홈을 가린다 - 아니면 같은 기록이 다른 바이트가 된다."""
        monkeypatch.setenv("HOME", str(tmp_path))
        moved = _load()
        assert moved.mask(f"{xp.ACCOUNT.pw_dir}/.codex/x") == "~/.codex/x"

    def test_a_worktree_copy_masks_the_main_checkout(self, tmp_path: Path) -> None:
        """🔴 worktree 의 사본에서 돌리면 저장소 경로가 `~/...` 로 남았다 - 주 체크아웃을 가린다."""
        git = shutil.which("git")
        assert git is not None
        main = tmp_path / "main"
        (main / "scripts").mkdir(parents=True)
        shutil.copy2(SCRIPT, main / "scripts" / SCRIPT.name)
        wt = main / "runs" / "wt"
        for args in (
            ["init", "-q", str(main)],
            ["-C", str(main), "add", "."],
            ["-C", str(main), "-c", "user.name=t", "-c", "user.email=t@t.test", "commit",
             "-qm", "x"],
            ["-C", str(main), "worktree", "add", "-q", str(wt)],
        ):
            subprocess.run([git, *args], capture_output=True, check=True)
        spec = importlib.util.spec_from_file_location("publish_wt", wt / "scripts" / SCRIPT.name)
        assert spec is not None and spec.loader is not None
        copy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy)
        assert main.resolve() == copy.REPO


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
        # 🔴 기록의 주 형식 - 이스케이프 뒤에 온 토큰 · 글 안의 JSON (이벤트의 명령 출력)
        (json.dumps({"item": {"aggregated_output": f"total 1\n{FAKE_KEY}\n"}}), "API 키 (sk-)"),
        (json.dumps({"out": json.dumps({"refresh_token": "x"})}), "인증 필드"),
        (json.dumps({"creator_account_id": FAKE_UUID}), "인증 필드"),
        (json.dumps({"out": json.dumps({"creator_user_id": FAKE_USER_ID})}), "계정 식별자"),
        ("cd /Users/someone-else/x", "가리지 못한 홈 경로"),
    ])
    def test_a_secret_stops_everything_and_is_not_printed(
        self, tmp_path: Path, text: str, kind: str
    ) -> None:
        """🔴 하나라도 보이면 아무것도 쓰지 않는다 - 보고에는 자리와 종류만 싣는다."""
        root = _root(tmp_path, {"XC001/clean.txt": "ok\n", "XC002/write-1.jsonl": f"a\n{text}\n"})
        out = tmp_path / "out"
        found = xp.publish([root], out)
        assert f"stage9/XC002/write-1.jsonl:2 · {kind}" in found
        assert {f.split(":")[0] for f in found} == {"stage9/XC002/write-1.jsonl"}
        assert not out.exists()
        assert not any(text in f for f in found)

    def test_a_bare_openai_user_id_is_found(self, tmp_path: Path) -> None:
        root = _root(tmp_path, {"XC001/a.txt": f"creator {FAKE_USER_ID}\n"})
        assert xp.publish([root], None) == ["stage9/XC001/a.txt:1 · OpenAI 사용자 ID"]

    @pytest.mark.parametrize("make", ["missing", "file", "empty"])
    def test_a_record_that_was_not_scanned_is_not_clean(self, tmp_path: Path, make: str) -> None:
        """🔴 [실측] 오타 · 파일 · 빈 폴더가 「0건 · 썼다」였다 - 빈 묶음이 기록처럼 공개된다."""
        root = tmp_path / "stage9"
        if make == "file":
            root.write_text(f"key={FAKE_KEY}\n", encoding="utf-8")
        elif make == "empty":
            (root / "XC001" / "__pycache__").mkdir(parents=True)
        out = tmp_path / "out"
        with pytest.raises(ValueError, match="훑을 파일이 없다"):
            xp.publish([root], out)
        assert not out.exists()

    def test_two_records_with_one_name_are_refused(self, tmp_path: Path) -> None:
        """뒤의 묶음이 앞의 것을 말없이 덮었다 (rc 0)."""
        a = _root(tmp_path / "a", {"XC001/a.txt": "x\n"})
        b = _root(tmp_path / "b", {"XC001/b.txt": "y\n"})
        with pytest.raises(ValueError, match="이름이 같은"):
            xp.publish([a, b], tmp_path / "out")
        assert not (tmp_path / "out").exists()

    def test_a_failure_while_staging_leaves_no_temp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """둘째 묶음을 쓰다 깨지면 첫 묶음의 임시 파일(가린 글)이 공개 폴더에 남았다."""
        first = _root(tmp_path / "x", {"XC001/a.txt": "x\n"}).rename(tmp_path / "x" / "first")
        second = _root(tmp_path / "y", {"XC001/b.txt": "y\n"}).rename(tmp_path / "y" / "second")
        real = xp.tempfile.NamedTemporaryFile
        made: list[int] = []

        def flaky(*args: Any, **kwargs: Any) -> Any:
            if made:
                raise OSError("디스크가 찼다")
            made.append(1)
            return real(*args, **kwargs)

        monkeypatch.setattr(xp.tempfile, "NamedTemporaryFile", flaky)
        out = tmp_path / "out"
        with pytest.raises(OSError, match="디스크"):
            xp.publish([first, second], out)
        assert list(out.iterdir()) == []

    def test_a_blocked_target_writes_nothing_and_leaves_no_temp(self, tmp_path: Path) -> None:
        """[실측] 둘째 묶음에서 깨지면 첫 묶음은 이미 바뀌었고 .tmp 가 남았다."""
        first = _root(tmp_path / "x", {"XC001/a.txt": "x\n"}).rename(tmp_path / "x" / "first")
        second = _root(tmp_path / "y", {"XC001/b.txt": "y\n"}).rename(tmp_path / "y" / "second")
        out = tmp_path / "out"
        (out / "second.jsonl").mkdir(parents=True)
        with pytest.raises(ValueError, match="파일이 아닌"):
            xp.publish([first, second], out)
        assert sorted(p.name for p in out.iterdir()) == ["second.jsonl"]

    def test_check_writes_nothing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        root = _root(tmp_path, {"XC001/a.txt": "x\n"})
        assert xp.main(["--check", str(root)]) == 0
        assert "0건" in capsys.readouterr().out
        assert [p.name for p in tmp_path.iterdir()] == ["stage9"]
