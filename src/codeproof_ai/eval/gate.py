"""codex 가 쓴 쌍의 관문 - 기계로 보는 것만 (DESIGN §7.10d 「관문」).

    codeproof decoy gate [ID ...] --corpus corpus/xauthor/codex [--race-runs 30]

저자는 상자에서, 하네스는 권한 프로필 아래서 같은 명령을 돈다. 쌍 하나가 넘으려면 전부 통과한다:

    validate  `decoy validate --strict` 와 같다 - 경고도 센다
    proof     반증 두 줄 - decoy 는 못 깨고 twin 은 깬다 (`python -O` 판 포함)
    mutants   약화 하나 이상 · 안전한 변형 하나 이상이 기대대로 갈린다
              (경쟁 약화는 race_runs 번 모두 깨진다)
    neutral   neutral 내보내기가 줄 수를 지키고 모듈 docstring 한 줄만 「목적.」으로 바꾼다
    cues      산문 주석이 없다 · 함수 · 클래스 docstring 은 guard_lines 안에만 ·
              twin 은 decoy 에 없는 docstring 을 더하지 않는다
    plan      도출한 가드 위치가 `corpus/plan.py` 에서 그 분류의 칸 안이다

🔴 목표 150쌍 코퍼스에는 걸지 않는다 - cues 는 §7.10d 가 새로 정한 규칙이고, 그 코퍼스의
   1·2라운드 쌍에는 mutants.py 가 없다.
🔴 모델이 쓴 코드(증명 · 변이)를 실행한다 - 하네스는 이 명령을 권한 프로필 아래서 돈다.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.corpus.decoy import DecoyLoadError, load_decoy, validate_decoy
from codeproof_ai.corpus.mutants import MutantError, apply, breaks, load_mutants, mutant_alias
from codeproof_ai.corpus.plan import PLAN
from codeproof_ai.corpus.proof import run_proof
from codeproof_ai.corpus.shape import classify
from codeproof_ai.eval.export import neutral_docstring

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.corpus.decoy import DecoyRecord

RACE_RUNS = 30
"""경쟁 약화를 돌리는 횟수 - `codeproof decoy mutants` 와 같다 (교훈 #51)."""

_DIRECTIVE = re.compile(r"#!|#\s*(?:noqa\b|type:|pragma\b|pyright:|mypy:|-\*- coding)")
"""산문이 아닌 주석 - 도구에게 하는 지시다."""


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str = ""


def gate(pair_dir: Path, workdir: Path, *, race_runs: int = RACE_RUNS) -> tuple[Check, ...]:
    """쌍 하나의 관문. 앞 검사가 실패해도 뒤 검사를 돈다 - 저자가 문제를 한 번에 받는다."""
    rec, validate = _validate(pair_dir)
    checks = (
        validate,
        _proof(pair_dir),
        _mutants(pair_dir, workdir, race_runs),
        _neutral(pair_dir),
    )
    if rec is None:
        skipped = "meta.toml 을 읽지 못해 보지 못했다"
        return (*checks, Check("cues", False, skipped), Check("plan", False, skipped))
    return (*checks, _cues(rec), _plan(rec))


def _validate(pair_dir: Path) -> tuple[DecoyRecord | None, Check]:
    try:
        rec = load_decoy(pair_dir)
    except DecoyLoadError as exc:
        return None, Check("validate", False, str(exc))
    # 수용 표기된 경고는 이미 빠져 있고, 쓰이지 않는 표기는 V11 이 따로 낸다
    found = validate_decoy(rec)
    return rec, Check("validate", not found, "; ".join(f"{v.rule} {v.message}" for v in found))


def _proof(pair_dir: Path) -> Check:
    try:
        result = run_proof(pair_dir)
    except Exception as exc:  # 모델이 쓴 증명은 무엇이든 던질 수 있다 - 관문은 보고한다
        return Check("proof", False, f"{type(exc).__name__}: {exc}")
    return Check("proof", result.ok, result.failure or "")


def _mutants(pair_dir: Path, workdir: Path, race_runs: int) -> Check:
    try:
        mutants = load_mutants(pair_dir)
    except MutantError as exc:
        return Check("mutants", False, str(exc))
    if not any(m.expect_broken for m in mutants) or all(m.expect_broken for m in mutants):
        return Check("mutants", False, "약화와 안전한 변형이 하나 이상씩 있어야 한다")
    source = (pair_dir / "decoy.py").read_text(encoding="utf-8")
    wrong: list[str] = []
    for i, mutant in enumerate(mutants):
        runs = race_runs if mutant.racy else 1
        try:
            apply(source, mutant)  # 낡은 치환은 여기서 MutantError 다
            broke = sum(
                breaks(pair_dir, mutant, workdir, mutant_alias(pair_dir, i, r)) for r in range(runs)
            )
        except Exception as exc:  # 낡은 치환 · 증명을 읽다 던진 것 - 모두 실패로 보고한다
            wrong.append(f"「{mutant.label}」 {type(exc).__name__}: {exc}")
            continue
        if broke != (runs if mutant.expect_broken else 0):
            want = "약화" if mutant.expect_broken else "안전"
            wrong.append(f"「{mutant.label}」 ({want}) 깨짐 {broke}/{runs}")
    return Check("mutants", not wrong, "; ".join(wrong))


def neutral_problem(source: str) -> str | None:
    """neutral 내보내기가 줄 수를 지키고 모듈 docstring 한 줄만 「목적.」으로 바꾸는가.

    아니면 그 이유를 낸다. 줄 번호가 그대로여야 정답 구간(미끼 · 가드 · twin)이 맞는다
    (DESIGN §7.10c).
    """
    try:
        new = neutral_docstring(source)
        purpose = (ast.get_docstring(ast.parse(source)) or "").partition(" - ")[0]
        neutral = ast.get_docstring(ast.parse(new))
    except (ValueError, SyntaxError) as exc:
        return str(exc)
    before, after = source.split("\n"), new.split("\n")
    if len(before) != len(after):
        return f"줄 수가 바뀐다 ({len(before)} → {len(after)})"
    changed = sum(x != y for x, y in zip(before, after, strict=True))
    if changed != 1:
        return f"바뀌는 줄이 {changed}개다 - 모듈 docstring 한 줄이어야 한다"
    if neutral != f"{purpose.rstrip('.')}.":
        return "모듈 docstring 이 「목적.」 한 줄이 되지 않는다"
    return None


def _neutral(pair_dir: Path) -> Check:
    problems = []
    for name in ("decoy.py", "twin.py"):
        try:
            problem = neutral_problem((pair_dir / name).read_text(encoding="utf-8"))
        except OSError as exc:
            problem = str(exc)
        if problem:
            problems.append(f"{name}: {problem}")
    return Check("neutral", not problems, "; ".join(problems))


def prose_comments(source: str) -> list[int]:
    """산문 주석이 있는 줄 - 도구 지시(`# noqa` · `# type:` 등)는 빼고 센다."""
    return [
        tok.start[0]
        for tok in tokenize.generate_tokens(io.StringIO(source).readline)
        if tok.type == tokenize.COMMENT and not _DIRECTIVE.match(tok.string)
    ]


def inner_docstrings(source: str) -> list[tuple[int, int, str]]:
    """함수 · 클래스 docstring 의 (시작 줄, 끝 줄, 내용).

    중첩 관계는 쓰지 않으므로 ast.walk 로 모은다 (B3 은 둘러싼 함수를 찾을 때의 규칙이다).
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.append((first.lineno, first.end_lineno or first.lineno, first.value.value))
    return found


def _cues(rec: DecoyRecord) -> Check:
    """단서 규칙 - 단서는 claude 가 더 쓴다 (§7.10b). 새면 결과가 「더 짚는다」 쪽으로 기운다."""
    problems = []
    try:
        for name, source in (("decoy.py", rec.decoy_source), ("twin.py", rec.twin_source)):
            if lines := prose_comments(source):
                problems.append(f"{name}: 산문 주석 {', '.join(map(str, lines))}행")
        decoy_docs = inner_docstrings(rec.decoy_source)
        twin_docs = inner_docstrings(rec.twin_source)
    except (tokenize.TokenError, SyntaxError) as exc:
        return Check("cues", False, f"읽지 못했다: {exc}")
    guard = rec.guard
    outside = [start for start, end, _ in decoy_docs if end < guard.start or start > guard.end]
    if outside:
        problems.append(f"decoy.py: guard_lines 밖의 함수 · 클래스 docstring {outside}행")
    known = {text for _, _, text in decoy_docs}
    if added := [start for start, _, text in twin_docs if text not in known]:
        problems.append(f"twin.py: decoy 에 없는 docstring {added}행")
    return Check("cues", not problems, "; ".join(problems))


def _plan(rec: DecoyRecord) -> Check:
    try:
        shape = classify(rec.decoy_source, rec.lure.start, rec.guard_symbol)
    except Exception as exc:  # 도출이 실패하면 칸을 말할 수 없다 - 실패로 보고한다
        return Check("plan", False, f"가드 위치를 도출하지 못했다: {exc}")
    cells = PLAN[rec.trap_kind]
    if shape in cells:
        return Check("plan", True)
    allowed = ", ".join(sorted(c.value for c in cells))
    return Check(
        "plan", False, f"가드 위치 {shape.value} 는 {rec.trap_kind.value} 의 칸({allowed})이 아니다"
    )
