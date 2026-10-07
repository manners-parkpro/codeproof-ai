"""codex 저자 실행의 상자 · 점검표 · 판정 (DESIGN §7.10d) - codex 를 부르지 않는 부분만 본다.

🔴 판정이 공허하면 격리가 깨진 실행이 「통과」로 시작한다 - 판정마다 우는 입력을 같이 둔다.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.corpus.decoy import pair_dirs

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "xauthor.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("xauthor", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


xa = _load()
VENV = Path("/Users/Shared/xauthor-venv-test")
BOX = Path("/Users/Shared/xauthor-box-test")
Row = tuple[str, str, bool]


def _table() -> list[Row]:
    """실제 클론 · 홈 경로를 쓰지 않는다 - 받은 사람의 경로에 공백이 있어도 시험은 같아야 한다."""
    fake = Path("/Users/someone")
    table: list[Row] = xa.probes(BOX, VENV, repo=fake / "repo", home=fake, user_tmp=fake / "tmp")
    return table


def _reported(line: str) -> str:
    """codex 0.158.0 이 보고하는 명령의 모양 [실측 · runs/agent/codex-cli/raw 426건]."""
    return f'/bin/zsh -c "{line}"' if "'" in line else f"/bin/zsh -c '{line}'"


def _events(path: Path, items: list[dict[str, object]]) -> Path:
    lines = [json.dumps({"type": "item.started", "item": {"type": "command_execution"}})]
    lines += [
        json.dumps({"type": "item.completed", "item": {"type": "command_execution", **i}})
        for i in items
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _all_ok(table: list[Row]) -> list[dict[str, object]]:
    return [
        {"command": _reported(xa.check_line(*row)), "aggregated_output": f"CANARY-OK-{row[0]}\n"}
        for row in table
    ]


def _clean_check_output(table: list[Row]) -> str:
    return "\n".join([*(f"CANARY-OK-{name}" for name, _, _ in table), "WRITABLE-TRIED 20 WROTE 0"])


class TestTheBox:
    def test_profile_is_the_declared_allowlist(self) -> None:
        """선언 「상자」 행 - :tmpdir 는 상자 TMPDIR 까지 막아 뺐다 (수집 전 수정 ①)."""
        p = xa.profile(VENV)
        assert p.startswith('{":root"="none"')
        assert f'"{VENV}"="read"' in p
        assert '"/private/var/tmp"="none"' in p
        assert ":tmpdir" not in p

    def test_environment_is_minimal(self) -> None:
        env = xa.environment(BOX, VENV)
        assert set(env) == {"PATH", "HOME", "TMPDIR", "CODEX_HOME", "LANG"}
        assert env["HOME"].startswith(str(BOX)) and env["TMPDIR"].startswith(str(BOX))
        assert env["PATH"].startswith(f"{VENV}/bin:")
        assert env["CODEX_HOME"] == str(Path.home() / ".codex")  # 인증을 복사하지 않는다

    def test_only_the_canary_keeps_a_session_record(self, tmp_path: Path) -> None:
        last = tmp_path / "last.txt"
        assert "--ephemeral" in xa.exec_args(BOX, VENV, "p", last, ephemeral=True)
        assert "--ephemeral" not in xa.exec_args(BOX, VENV, "p", last, ephemeral=False)

    def test_the_login_shell_is_off(self, tmp_path: Path) -> None:
        """🔴 로그인 셸의 path_helper 가 venv 를 /usr/bin 뒤로 민다 (수집 전 수정 ⑤)."""
        args = xa.exec_args(BOX, VENV, "p", tmp_path / "last.txt", ephemeral=True)
        assert args[args.index("allow_login_shell=false") - 1] == "-c"

    def test_no_sandbox_flag_overrides_the_profile(self, tmp_path: Path) -> None:
        """🔴 `--sandbox` 를 주면 프로필 대신 옛 workspace-write 가 걸린다 (수집 전 수정 ⑥)."""
        args = xa.exec_args(BOX, VENV, "p", tmp_path / "last.txt", ephemeral=True)
        assert not {"--sandbox", "-s"} & set(args)
        assert args[args.index('default_permissions="box"') - 1] == "-c"


class TestProbes:
    def test_it_checks_both_directions(self) -> None:
        """막혀야 하는 것만 보면 상자가 아무것도 못 해도 통과한다 - 되어야 하는 것도 본다."""
        table = _table()
        names = {name for name, _, _ in table}
        assert {"REPO", "CODEX-HOME", "VAR-TMP", "NET"} <= names
        assert {"BOX-TMP", "VENV-FIRST", "GATE"} <= names
        assert len(names) == len(table)

    def test_no_quotes_or_dollars(self) -> None:
        """🔴 카나리는 시킨 명령이 보고된 명령에 그대로 있는지로 판정한다.

        codex 가 그대로 보고하는 것을 본 것은 홑따옴표로 감싼 명령뿐이다 - `$` · 따옴표는 뺀다.
        """
        for row in _table():
            line = xa.check_line(*row)
            assert not set(line) & {"'", '"', "$", "\\"}, line

    def test_an_odd_path_is_refused(self) -> None:
        with pytest.raises(ValueError, match="점검표"):
            xa.probes(Path("/Users/Shared/with space"), VENV)


class TestCheckLine:
    @pytest.mark.parametrize(
        ("probe", "allowed", "mark"),
        [
            ("true", True, "CANARY-OK-X"),
            ("false", True, "CANARY-BAD-X"),
            ("true", False, "CANARY-BAD-X"),
            ("false", False, "CANARY-OK-X"),
        ],
    )
    def test_the_line_marks_what_happened(self, probe: str, allowed: bool, mark: str) -> None:
        line = xa.check_line("X", probe, allowed)
        done = subprocess.run(["/bin/sh", "-c", line], capture_output=True, text=True, check=True)
        assert done.stdout.split("\n")[0] == mark


class TestJudgeCheck:
    def test_a_clean_run_holds(self) -> None:
        """대조군 - 아래 우는 입력이 입력을 못 넣어서 우는 것이 아님을 가른다."""
        table = _table()
        ok, summary = xa.judge_check(_clean_check_output(table), table)
        assert ok, summary

    @pytest.mark.parametrize(
        "spoil",
        [
            lambda out: out.replace("CANARY-OK-REPO", "CANARY-BAD-REPO"),
            lambda out: out.replace("CANARY-OK-GATE\n", ""),
            lambda out: out.replace("WROTE 0", "WROTE 1") + "\nCANARY-BAD-WRITE '/private/var/tmp'",
            lambda out: out.replace("WRITABLE-TRIED 20", "WRITABLE-TRIED 0"),
            lambda out: out.replace("\nWRITABLE-TRIED 20 WROTE 0", ""),
        ],
        ids=["leak", "missing-ok", "wrote", "tried-nothing", "loop-did-not-run"],
    )
    def test_it_cries(self, spoil: object) -> None:
        table = _table()
        assert callable(spoil)
        ok, summary = xa.judge_check(spoil(_clean_check_output(table)), table)
        assert not ok, summary


class TestJudgeCanary:
    def test_everything_as_expected(self, tmp_path: Path) -> None:
        """대조군 - 감싼 명령도 시킨 명령으로 알아본다."""
        table = _table()
        verdict = xa.judge_canary(_events(tmp_path / "e.jsonl", _all_ok(table)), table)
        assert set(verdict.values()) == {"OK"}, verdict

    def test_a_leak_is_bad(self, tmp_path: Path) -> None:
        table = _table()
        items = _all_ok(table)
        items[0]["aggregated_output"] = "CANARY-BAD-REPO\n"
        assert xa.judge_canary(_events(tmp_path / "e.jsonl", items), table)["REPO"] == "BAD"

    def test_a_skipped_command_is_not_ok(self, tmp_path: Path) -> None:
        """🔴 모델이 명령을 건너뛰거나 고치면 「막혔다」가 아니라 「안 돌림」이다."""
        table = _table()
        items = [i for i in _all_ok(table) if "README" not in str(i["command"])]
        assert xa.judge_canary(_events(tmp_path / "e.jsonl", items), table)["REPO"] == "안 돌림"

    def test_a_probe_inside_another_command_does_not_count(self, tmp_path: Path) -> None:
        """`ls <홈>` 은 `ls <홈>/.codex` 안에도 있다 - 표지로 가르지 않으면 남의 출력을 읽는다."""
        table = _table()
        items = [i for i in _all_ok(table) if "CANARY-OK-USER-HOME" not in str(i["command"])]
        verdict = xa.judge_canary(_events(tmp_path / "e.jsonl", items), table)
        assert verdict["USER-HOME"] == "안 돌림"
        assert verdict["CODEX-HOME"] == "OK"

    def test_the_marker_in_the_command_does_not_count(self, tmp_path: Path) -> None:
        """명령 문자열에도 표지가 있다 - 출력에 OK 표지가 없으면 OK 가 아니다."""
        table = _table()
        items = _all_ok(table)
        items[0]["aggregated_output"] = ""
        assert xa.judge_canary(_events(tmp_path / "e.jsonl", items), table)["REPO"] == "BAD"

    def test_the_prompt_carries_every_line(self) -> None:
        table = _table()
        prompt = xa.canary_prompt("xauthor-canary-1", table)
        assert "xauthor-canary-1" in prompt
        assert all(xa.check_line(*row) in prompt for row in table)


class TestModelInputTraces:
    def _rollout(self, path: Path, records: list[dict[str, object]]) -> Path:
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        return path

    def _message(self, role: str, content: str) -> dict[str, object]:
        payload = {"type": "message", "role": role, "content": content}
        return {"type": "response_item", "payload": payload}

    def test_counts_only_model_input_outside_our_prompt(self, tmp_path: Path) -> None:
        nonce = "xauthor-canary-1"
        tool_output = {"type": "custom_tool_call_output", "output": "cat: /x/codeproof-ai: denied"}
        rollout = self._rollout(tmp_path / "r.jsonl", [
            {"type": "session_meta", "payload": {"instructions": "built-in"}},
            self._message("user", f"{nonce} cat /x/codeproof-ai/README.md"),
            {"type": "response_item", "payload": tool_output},
            self._message("assistant", "codeproof"),
        ])
        assert not any(xa.model_input_traces(rollout, nonce).values())

    def test_the_inventory_lists_input_outside_our_prompt(self, tmp_path: Path) -> None:
        """선언 「상자」 행 - 카나리 지시 밖의 입력을 한 줄씩, 권한 목록은 경로를 가려 싣는다."""
        nonce = "xauthor-canary-1"
        entry = {"path": {"type": "path", "path": str(BOX)}, "access": "write"}
        rollout = self._rollout(tmp_path / "r.jsonl", [
            {"type": "turn_context", "payload": {"permission_profile": {"entries": [entry]}}},
            self._message("developer", "sandbox notes"),
            self._message("user", f"{nonce} commands"),
            self._message("assistant", "DONE"),
        ])
        lines = xa.input_inventory(rollout, nonce, {str(BOX): "<box>"})
        assert len(lines) == 2
        assert lines[0].startswith("turn_context") and "write <box>" in lines[0]
        assert str(BOX) not in lines[0]
        assert lines[1].startswith("developer") and "sandbox notes" in lines[1]

    def test_the_inventory_hides_account_ids(self, tmp_path: Path) -> None:
        """🔴 공개 요약에 싣는다 - session_meta 는 키만 (계정 식별자가 든다 [실측 · 카나리])."""
        meta = {"creator_user_id": "user-SECRET", "creator_account_id": "acct-SECRET"}
        rollout = self._rollout(tmp_path / "r.jsonl", [{"type": "session_meta", "payload": meta}])
        (line,) = xa.input_inventory(rollout, "xauthor-canary-1", {})
        assert "creator_user_id" in line
        assert "SECRET" not in line

    def test_builtin_instructions_are_not_counted(self, tmp_path: Path) -> None:
        """codex 내장 지시만 빼고 센다 - 그 밖의 session_meta 필드는 센다 (대조)."""
        meta = {"base_instructions": "a SKILL.md, AGENTS.md, memory, or approval block",
                "cwd": "/x/codeproof-ai"}
        rollout = self._rollout(tmp_path / "r.jsonl", [{"type": "session_meta", "payload": meta}])
        traces = xa.model_input_traces(rollout, "xauthor-canary-1")
        assert traces["memor"] == 0
        assert traces["codeproof"] == 1

    def test_a_trace_in_developer_input_counts(self, tmp_path: Path) -> None:
        rollout = self._rollout(tmp_path / "r.jsonl", [
            self._message("developer", "from memory: the decoy pairs"),
        ])
        traces = xa.model_input_traces(rollout, "xauthor-canary-1")
        assert traces["decoy"] == 1
        assert traces["memor"] == 1


# ── 저자가 상자에서 읽을 수 있는 것 ─────────────────────────────────────────────

REPO = SCRIPT.parents[1]
_PAIR_ID = re.compile(r"\bD(\d{3})\b")


def _claude_names() -> set[str]:
    """claude 쌍의 decoy · twin 이 정의한 고유한 함수 · 클래스 이름 - dunder 와 짧은 이름은 뺀다."""
    names = set()
    for pair in pair_dirs(REPO / "corpus" / "decoys"):
        for name in ("decoy.py", "twin.py"):
            for node in ast.walk(ast.parse((pair / name).read_text(encoding="utf-8"))):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    n = node.name
                    if not n.startswith("__") and "_" in n.strip("_") and len(n) >= 8:
                        names.add(n)
    return names


def _claude_traces(text: str, names: set[str]) -> list[str]:
    """claude 쌍 번호(D001~D150)와 고유 이름.

    D100~D107 은 Ruff pydocstyle 룰 코드와 겹쳐 번호로 보지 않는다 - 이름 축이 대신 본다.
    """
    found = [
        m[0] for m in _PAIR_ID.finditer(text)
        if 1 <= int(m[1]) <= 150 and not 100 <= int(m[1]) <= 107
    ]
    return found + [n for n in sorted(names) if re.search(rf"\b{re.escape(n)}\b", text)]


class TestNothingOfClaudePairsInTheBox:
    """§7.10d 「쓰는 입력」 - claude 쌍의 코드는 주지 않는다 (claude 쌍에서 뽑은 설계 공간이다).

    venv 는 프로필에서 읽기 허용이라 하네스 소스(wheel = src/codeproof_ai)가 상자에서 그대로 읽힌다.
    [실측] 고치기 전 그 소스에 claude 쌍 참조 24곳 · decoy 고유 함수 이름 셋이 있었다.
    🔴 §7.10d 측정이 끝나기 전에는 하네스 소스에 쌍 번호 · 쌍의 함수 이름을 쓰지 않는다 -
       DESIGN 에 쓴다.
    """

    def test_what_the_author_can_read_names_no_claude_pair(self) -> None:
        names = _claude_names()
        readable = [
            *(REPO / "src" / "codeproof_ai").rglob("*.py"),
            *(p for p in (REPO / "corpus" / "decoys" / "_TEMPLATE").rglob("*") if p.is_file()),
        ]
        found = {
            str(p.relative_to(REPO)): hits
            for p in readable
            if (hits := _claude_traces(p.read_text(encoding="utf-8"), names))
        }
        assert not found, found

    def test_the_scan_catches_a_pair_number_and_a_name(self) -> None:
        """대조 - 스캔이 공허하면 위 테스트는 무엇이 새도 통과한다."""
        names = _claude_names()
        assert len(names) >= 50
        some = sorted(names)[0]
        assert _claude_traces("[실측] D051 은 두 단계 건너다", names) == ["D051"]
        assert _claude_traces(f"`{some}` 를 가드로 쓴다", names) == [some]
        assert _claude_traces("FP 66건 중 45건이 D103 이었다", names) == []
