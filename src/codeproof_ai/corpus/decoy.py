"""D층 decoy 로더와 검증기.

decoy 란 **버그처럼 보이지만 증명 가능하게 안전한** 코드다.
근거 없는 decoy 는 그냥 "아무도 확인 안 한 코드" 이고, 그건 이 프로젝트가
비판하는 바로 그것 - 증거의 부재를 부재의 증거로 착각하는 것 - 과 같아진다.

디렉터리 구조 (하나가 한 건):

    corpus/decoys/D001-guarded-dict-access/
    ├── meta.toml    메타데이터 · 안전 근거
    ├── decoy.py     안전한 버전  → 여기서의 모든 지적은 FP
    └── twin.py      가드만 제거한 진짜 버그 버전 → 양성

코드를 실제 .py 로 두는 이유: 파싱·린트·diff 가 전부 기계적으로 검증 가능해진다.
"""

from __future__ import annotations

import ast
import difflib
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from pathlib import Path

# 가드와 무관한 변경이 얼마나 섞여도 "가드만 다르다" 로 볼 것인가.
# Juliet 의 goodG2B/goodB2G 는 사실상 한 구문만 다르다. 여유를 조금 둔다.
MAX_TWIN_DIFF_LINES = 12

# "안전하다" 를 반복하기만 하는 근거를 막는다.
MIN_JUSTIFICATION_CHARS = 60

# 서로 다른 낱말이 이보다 적으면 결론만 반복한 것으로 본다.
MIN_JUSTIFICATION_WORDS = 8

_RANGE_ARITY = 2

_EMPTY_PHRASES = (
    "안전하다",
    "문제없다",
    "괜찮다",
    "이상 없다",
    "safe",
    "no problem",
    "fine",
)


class TrapKind(StrEnum):
    """미끼의 종류.

    SecLLMHolmes 의 non-trivial augmentation(NT1-NT6) 분류를
    보안이 아니라 일반 코드리뷰로 옮긴 것이다.
    """

    UPSTREAM_VALIDATION = "upstream_validation"
    """상류에서 이미 전수 검증됨. 아래 접근이 무방비로 보인다."""

    CALLER_HELD_LOCK = "caller_held_lock"
    """호출부가 락을 쥐고 있어 경쟁이 불가능하다."""

    ENCLOSING_CONTEXT = "enclosing_context"
    """바깥 스코프의 context manager 가 자원을 보장한다."""

    CONTRACT_HALF_OPEN = "contract_half_open"
    """계약상 반열린 구간이라 off-by-one 처럼 보이는 쪽이 맞다."""

    CONSTANT_ONLY_SINK = "constant_only_sink"
    """위험 API 지만 외부 입력이 전혀 닿지 않는다 (NT4)."""

    TYPE_NARROWED = "type_narrowed"
    """타입이 이미 좁혀져 분기가 불필요하다."""

    MISLEADING_NAME = "misleading_name"
    """unsafe_/raw_ 접두사지만 실제로는 검증된 값 (NT1·NT2)."""

    NOOP_SHIM_NEIGHBOR = "noop_shim_neighbor"
    """진짜 sanitize 옆에 no-op shim 이 있어 혼동을 유발 (NT5·NT6)."""

    UNREACHABLE_BRANCH = "unreachable_branch"
    """도달 불가능한 분기라 결함이 실현되지 않는다."""

    IDEMPOTENT_RETRY = "idempotent_retry"
    """재시도가 멱등이라 중복 실행이 무해하다."""

    DEFENSIVE_COPY = "defensive_copy"
    """제자리 변형처럼 보이지만 경계에서 복사본을 받는다."""

    BOUNDED_INPUT = "bounded_input"
    """무제한 할당처럼 보이지만 상류가 상한을 강제한다."""

    EXCEPTION_ABSORBED = "exception_absorbed"
    """광범위 except 가 정리 경로에만 있어 삼키는 것이 정확한 동작이다."""

    FROZEN_AFTER_INIT = "frozen_after_init"
    """가변 전역처럼 보이지만 초기화 후 불변이 강제된다."""


class Level(StrEnum):
    ERROR = "error"
    WARN = "warn"


@dataclass(frozen=True, slots=True)
class Violation:
    """검증 위반 1건."""

    rule: str
    level: Level
    message: str

    def __str__(self) -> str:
        mark = "✗" if self.level is Level.ERROR else "!"
        return f"  {mark} [{self.rule}] {self.message}"


@dataclass(frozen=True, slots=True)
class LineRange:
    """1-based 포함 구간."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 1 or self.end < self.start:
            msg = f"잘못된 구간: {self.start}-{self.end}"
            raise ValueError(msg)

    def overlaps(self, other: LineRange) -> bool:
        return self.start <= other.end and other.start <= self.end

    def within(self, total_lines: int) -> bool:
        return self.end <= total_lines

    @classmethod
    def parse(cls, raw: object, field_name: str) -> Self:
        if not isinstance(raw, list) or len(raw) != _RANGE_ARITY:
            msg = f"{field_name} 은 [시작, 끝] 두 정수여야 한다: {raw!r}"
            raise ValueError(msg)
        a, b = raw
        if not isinstance(a, int) or not isinstance(b, int):
            msg = f"{field_name} 원소는 정수여야 한다: {raw!r}"
            raise ValueError(msg)
        return cls(start=a, end=b)


@dataclass(frozen=True, slots=True)
class DecoyRecord:
    """decoy 1건.

    Attributes:
        decoy_id: 안정 식별자. 디렉터리명과 일치해야 한다.
        trap_kind: 미끼 종류.
        apparent_defect: 리뷰어가 무엇을 결함으로 볼 것인가 (미끼 설명).
        lure: decoy.py 에서 미끼가 보이는 줄.
        claim: 무엇이 안전한가.
        justification: 🔴 왜 안전한가. 기전을 명시해야 한다.
        guard_symbol: 방어가 있는 심볼.
        guard: 🔴 decoy.py 에서 방어가 실제로 있는 줄.
            **반드시 decoy.py 안이어야 한다** - 아래 V4 참조.
        twin_defect: twin.py 가 무슨 결함인지.
        acknowledged: 작성자가 의도적으로 수용한 WARN 규칙 id.
            ERROR 는 수용할 수 없다 - 수용 가능하면 그건 ERROR 가 아니다.
    """

    decoy_id: str
    trap_kind: TrapKind
    apparent_defect: str
    lure: LineRange
    claim: str
    justification: str
    guard_symbol: str
    guard: LineRange
    twin_defect: str
    acknowledged: frozenset[str]
    directory: Path = field(compare=False)
    decoy_source: str = field(compare=False, repr=False)
    twin_source: str = field(compare=False, repr=False)


class DecoyLoadError(Exception):
    """meta.toml 이 구조적으로 읽히지 않을 때."""


def load_decoy(directory: Path) -> DecoyRecord:
    """디렉터리 하나를 DecoyRecord 로 읽는다.

    구조적으로 읽을 수 없으면 DecoyLoadError 를 올린다.
    내용 규칙 위반은 여기서 보지 않는다 - validate_decoy 가 본다.
    """
    meta_path = directory / "meta.toml"
    decoy_path = directory / "decoy.py"
    twin_path = directory / "twin.py"

    for p in (meta_path, decoy_path, twin_path):
        if not p.is_file():
            msg = f"{directory.name}: {p.name} 이 없다"
            raise DecoyLoadError(msg)

    try:
        meta = tomllib.loads(meta_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = f"{directory.name}: meta.toml 파싱 실패 - {exc}"
        raise DecoyLoadError(msg) from exc

    try:
        bait = meta["bait"]
        safety = meta["safety"]
        twin = meta["twin"]
        return DecoyRecord(
            decoy_id=str(meta["decoy_id"]),
            trap_kind=TrapKind(str(meta["trap_kind"])),
            apparent_defect=str(bait["apparent_defect"]),
            lure=LineRange.parse(bait["lure_lines"], "bait.lure_lines"),
            claim=str(safety["claim"]),
            justification=str(safety["justification"]),
            guard_symbol=str(safety["guard_symbol"]),
            guard=LineRange.parse(safety["guard_lines"], "safety.guard_lines"),
            twin_defect=str(twin["defect"]),
            acknowledged=frozenset(
                str(r) for r in meta.get("acknowledged_warnings", ())
            ),
            directory=directory,
            decoy_source=decoy_path.read_text(encoding="utf-8"),
            twin_source=twin_path.read_text(encoding="utf-8"),
        )
    except KeyError as exc:
        msg = f"{directory.name}: meta.toml 에 필수 항목이 없다 - {exc}"
        raise DecoyLoadError(msg) from exc
    except ValueError as exc:
        msg = f"{directory.name}: meta.toml 값이 잘못됐다 - {exc}"
        raise DecoyLoadError(msg) from exc


def changed_lines_in_decoy(decoy_src: str, twin_src: str) -> list[LineRange]:
    """decoy 기준으로 twin 과 달라진 구간을 돌려준다 (1-based 포함)."""
    a = decoy_src.splitlines()
    b = twin_src.splitlines()
    ranges: list[LineRange] = []
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        # 순수 삽입(i1 == i2)은 decoy 쪽에 폭이 없다 - 경계 한 줄로 본다.
        start = i1 + 1
        end = max(i2, i1 + 1)
        ranges.append(LineRange(start=start, end=end))
    return ranges


def twin_changed_lines(decoy_src: str, twin_src: str) -> list[LineRange]:
    """twin 기준으로 decoy 와 달라진 구간 (1-based 포함).

    changed_lines_in_decoy 의 반대편이다. twin 의 결함 위치를 정하는 데 쓴다 -
    가드가 제거된 자리가 곧 결함 자리다.
    """
    a = decoy_src.splitlines()
    b = twin_src.splitlines()
    ranges: list[LineRange] = []
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        ranges.append(LineRange(start=j1 + 1, end=max(j2, j1 + 1)))
    return ranges


def decoy_lines_in_twin(decoy_src: str, twin_src: str, start: int, end: int) -> list[int]:
    """decoy 의 줄 구간(1-based 포함)을 twin 의 줄 번호로 옮긴다 - **같은 블록에 있는 줄만**.

    twin_changed_lines 와 같은 diff 를 쓴다. 바뀐 블록 안의 줄은 대응이 없어 버린다 -
    짐작으로 옮기면 정답 구간이 근거 없이 넓어진다 (DESIGN §7.10c 보조 ③).
    """
    a = decoy_src.splitlines()
    b = twin_src.splitlines()
    out: list[int] = []
    for tag, i1, i2, j1, _j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            continue
        out.extend(j1 + (ln - 1 - i1) + 1 for ln in range(start, end + 1) if i1 < ln <= i2)
    return out


def diff_size(decoy_src: str, twin_src: str) -> int:
    """양쪽에서 달라진 줄 수의 합.

    🔴 decoy 쪽만 세면 안 된다 - decoy 가 11줄이면 twin 이 40줄 늘어나도
       decoy 쪽 변경은 11줄을 넘을 수 없어서 V6 이 영원히 발동하지 않는다.
    """
    a = decoy_src.splitlines()
    b = twin_src.splitlines()
    total = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            total += (i2 - i1) + (j2 - j1)
    return total


def _parses(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return f"{exc.msg} (line {exc.lineno})"
    return None


def _check_identity(rec: DecoyRecord) -> list[Violation]:
    """V7 - 식별자가 디렉터리명과 일치하는가."""
    if rec.decoy_id == rec.directory.name:
        return []
    return [
        Violation(
            "V7",
            Level.ERROR,
            f"decoy_id({rec.decoy_id}) 가 디렉터리명({rec.directory.name}) 과 다르다",
        )
    ]


def _check_parsing(rec: DecoyRecord) -> list[Violation]:
    """V2 - 두 파일이 유효한 파이썬인가."""
    out: list[Violation] = []
    for label, src in (("decoy.py", rec.decoy_source), ("twin.py", rec.twin_source)):
        if err := _parses(src):
            out.append(Violation("V2", Level.ERROR, f"{label} 가 파싱되지 않는다: {err}"))
    return out


def _check_justification(rec: DecoyRecord) -> list[Violation]:
    """V3 - 안전 근거가 기전을 설명하는가.

    결론만 반복하는 근거는 근거가 아니다. 그런 decoy 는
    "아무도 확인 안 한 코드" 와 구별되지 않는다.
    """
    out: list[Violation] = []
    just = rec.justification.strip()

    if len(just) < MIN_JUSTIFICATION_CHARS:
        out.append(
            Violation(
                "V3",
                Level.ERROR,
                f"안전 근거가 너무 짧다 ({len(just)}자 < {MIN_JUSTIFICATION_CHARS}자). "
                "무엇이 방어하는지 기전을 쓴다 - 결론만 반복하면 근거가 아니다",
            )
        )
    elif not any(c in just for c in ("때문", "므로", "이고", "따라", "because", "since")):
        out.append(
            Violation(
                "V3",
                Level.WARN,
                "안전 근거에 인과 연결어가 없다 - 기전이 아니라 주장만 적혔을 가능성",
            )
        )

    if just.lower() in _EMPTY_PHRASES or len(set(just.split())) < MIN_JUSTIFICATION_WORDS:
        out.append(Violation("V3", Level.ERROR, "안전 근거가 공허하다"))
    return out


def _check_visibility(rec: DecoyRecord, decoy_lines: int) -> list[Violation]:
    """V4·V10 - 가드와 미끼가 제시된 코드 안에서 보이는가.

    🔴 V4 가 이 검증기의 핵심이다.
       모델 API 비교에는 툴도 파일접근도 없다. 가드가 decoy.py 밖에 있으면
       리뷰어가 알 방법이 없고, 그건 decoy 가 아니라 알아맞히기 문제다.
    """
    out: list[Violation] = []

    if not rec.guard.within(decoy_lines):
        out.append(
            Violation(
                "V4",
                Level.ERROR,
                f"가드 구간 {rec.guard.start}-{rec.guard.end} 이 decoy.py 범위"
                f"(1-{decoy_lines}) 밖이다. 가드는 제시된 코드 안에서 보여야 한다 - "
                "밖에 있으면 리뷰어가 알 방법이 없고, 그건 decoy 가 아니라 함정문제다",
            )
        )
    if rec.guard_symbol not in rec.decoy_source:
        out.append(
            Violation("V4", Level.ERROR, f"guard_symbol '{rec.guard_symbol}' 이 decoy.py 에 없다")
        )
    else:
        out.extend(_check_guard_points_at_the_symbol(rec))
    if not rec.lure.within(decoy_lines):
        out.append(
            Violation(
                "V10",
                Level.ERROR,
                f"미끼 구간 {rec.lure.start}-{rec.lure.end} 이 decoy.py 범위 밖이다",
            )
        )
    return out


def _symbol_span(source: str, symbol: str) -> LineRange | None:
    """그 이름이 **정의되는** 줄 범위. 함수·클래스·모듈 수준 대입을 본다.

    못 찾으면 None - 그 이름이 정의가 아니라 참조로만 등장하는 경우다.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    found: LineRange | None = None

    def visit(node: ast.AST) -> None:
        nonlocal found
        for child in ast.iter_child_nodes(node):
            name = _defined_name(child)
            if name == symbol and found is None:
                decorators: list[ast.expr] = getattr(child, "decorator_list", [])
                start = min([child.lineno, *(d.lineno for d in decorators)])  # type: ignore[attr-defined]
                found = LineRange(start, child.end_lineno or start)  # type: ignore[attr-defined]
            visit(child)

    visit(tree)
    return found


def _defined_name(node: ast.AST) -> str | None:
    """이 노드가 정의하는 이름. 아니면 None."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return node.name
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                return t.id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _check_guard_points_at_the_symbol(rec: DecoyRecord) -> list[Violation]:
    """V13 - guard_lines 가 guard_symbol 과 **실제로 관계된 자리**인가.

    🔴 V4 는 「구간이 파일 안인가」와 「심볼이 파일에 있는가」를 **따로** 본다.
       둘 다 통과하면서 서로 다른 곳을 가리킬 수 있다 - 파일 안이지만
       엉뚱한 줄을 적어도 아무도 모른다.

    통과 조건은 둘 중 하나다:
      · 구간 안에 그 이름이 **글자로 등장**한다 (사용 자리 가드)
      · 구간이 그 이름의 **정의 범위와 겹친다** (정의 자리 가드)

    ⚠ 둘을 다 허용하는 이유: 가드는 심볼의 정의일 수도, 그 심볼을 **부르는
      자리**일 수도 있다. [실측] D026 은 `is_envelope` 의 정의(6-11)가 아니라
      호출부(15-16)가 가드이고 그게 맞다 - 처음에 정의만 허용했다가
      정당한 decoy 둘을 잘못 잡았다.
    """
    lines = rec.decoy_source.splitlines()
    window = lines[rec.guard.start - 1 : rec.guard.end]
    if any(rec.guard_symbol in line for line in window):
        return []

    span = _symbol_span(rec.decoy_source, rec.guard_symbol)
    if span is None:
        return []
    if rec.guard.end < span.start or span.end < rec.guard.start:
        return [
            Violation(
                "V13",
                Level.ERROR,
                f"guard_lines {rec.guard.start}-{rec.guard.end} 에 "
                f"guard_symbol '{rec.guard_symbol}' 이 나오지도 않고 "
                f"그 정의({span.start}-{span.end})와 겹치지도 않는다 - "
                "「가드가 여기 있다」가 거짓이다",
            )
        ]
    return []


def _diff_touches_symbol(rec: DecoyRecord, diffs: list[LineRange]) -> bool:
    """변경 구간 안에서 guard_symbol 을 참조하는 줄이 있는가.

    가드 우회(호출 제거)를 잡기 위한 것이다 - 가드 자체는 그대로 있고
    아무도 부르지 않게 되는 결함 형태.
    """
    lines = rec.decoy_source.splitlines()
    for d in diffs:
        for n in range(d.start, min(d.end, len(lines)) + 1):
            if rec.guard_symbol in lines[n - 1]:
                return True
    return False


def _check_twin(rec: DecoyRecord) -> list[Violation]:
    """V5·V6·V9·W2 - 쌍둥이가 '가드만 다른' 구조인가.

    Juliet 의 goodG2B/goodB2G 구조다. 이게 성립해야 짝 채점(P-C/P-V/P-B/P-R)이
    의미를 갖는다.
    """
    if rec.decoy_source == rec.twin_source:
        return [Violation("V5", Level.ERROR, "twin.py 가 decoy.py 와 완전히 같다")]

    out: list[Violation] = []
    diffs = changed_lines_in_decoy(rec.decoy_source, rec.twin_source)
    total_changed = diff_size(rec.decoy_source, rec.twin_source)

    if total_changed > MAX_TWIN_DIFF_LINES:
        out.append(
            Violation(
                "V6",
                Level.ERROR,
                f"twin 과의 차이가 {total_changed}줄로 너무 크다 (최대 {MAX_TWIN_DIFF_LINES}). "
                "'가드만 다르다' 가 성립해야 짝 채점이 의미를 갖는다",
            )
        )
    # V9 - 가드는 **제거**될 수도 있고 **우회**될 수도 있다.
    #
    # 실무 결함은 "검증기를 지웠다" 보다 "검증기를 부르는 걸 잊었다" 가 훨씬 흔하다.
    # 그래서 diff 가 가드 구간을 건드리거나, guard_symbol 을 참조하는 줄을
    # 건드리면 통과시킨다. 무관한 변경은 여전히 둘 다 만족하지 못한다.
    touches_guard = any(d.overlaps(rec.guard) for d in diffs)
    bypasses_guard = _diff_touches_symbol(rec, diffs)
    if not (touches_guard or bypasses_guard):
        spans = ", ".join(f"{d.start}-{d.end}" for d in diffs)
        out.append(
            Violation(
                "V9",
                Level.ERROR,
                f"twin 의 변경({spans})이 가드 구간({rec.guard.start}-{rec.guard.end})도 "
                f"'{rec.guard_symbol}' 참조도 건드리지 않는다. "
                "가드를 제거하거나 우회한 게 아니라 다른 데를 고친 것이다",
            )
        )

    both_parse = _parses(rec.decoy_source) is None and _parses(rec.twin_source) is None
    if both_parse and _signatures(rec.decoy_source) != _signatures(rec.twin_source):
        out.append(
            Violation(
                "W2",
                Level.WARN,
                "decoy 와 twin 의 최상위 시그니처가 다르다 - 가드 외 차이가 섞였을 수 있다",
            )
        )
    return out


def _check_proof(rec: DecoyRecord) -> list[Violation]:
    """V12 - 실행 가능한 반증 시도가 있는가.

    🔴 형식 검증은 안전 근거가 **참인지** 볼 수 없다. D015 는 가드로
       `threading.Semaphore(4)` 를 썼고(세마포어 4는 상호배제가 아니다)
       여기 있는 규칙을 **전부 통과**했다. 서면 근거만으로 「증명된 음성」을
       주장할 수 없다.

    proof.py 의 내용까지 여기서 돌리지는 않는다 - 임의 코드 실행은 검증기가
    아니라 테스트의 일이다. 여기서는 **있는지와 모양만** 본다.
    """
    path = rec.directory / "proof.py"
    if not path.is_file():
        return [
            Violation(
                "V12",
                Level.ERROR,
                "proof.py 가 없다 - 서면 근거만으로는 「증명된 음성」을 주장할 수 없다 "
                "(attack(mod) -> bool 를 노출하라)",
            )
        ]
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        return [Violation("V12", Level.ERROR, f"proof.py 가 파싱되지 않는다: {err}")]

    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "attack"
        ),
        None,
    )
    if fn is None:
        return [Violation("V12", Level.ERROR, "proof.py 에 attack 함수가 없다")]
    if len(fn.args.args) != 1:
        return [
            Violation(
                "V12",
                Level.ERROR,
                f"attack 은 인자 1개(mod)를 받는다 - 지금은 {len(fn.args.args)}개",
            )
        ]
    return []


def validate_decoy(rec: DecoyRecord) -> list[Violation]:
    """decoy 1건의 내용 규칙을 검사한다.

    ERROR 가 하나라도 있으면 그 decoy 는 코퍼스에 넣을 수 없다.
    WARN 은 기록하되 막지 않는다.
    """
    decoy_lines = len(rec.decoy_source.splitlines())
    found = [
        *_check_identity(rec),
        *_check_parsing(rec),
        *_check_justification(rec),
        *_check_visibility(rec, decoy_lines),
        *_check_twin(rec),
        *_check_proof(rec),
    ]
    # 작성자가 수용한 WARN 은 내린다. ERROR 는 수용 대상이 아니다 -
    # 수용 가능한 규칙이면 애초에 ERROR 로 두면 안 된다.
    kept = [
        v for v in found if v.level is Level.ERROR or v.rule not in rec.acknowledged
    ]
    stale = rec.acknowledged - {v.rule for v in found}
    kept.extend(
        Violation(
            "V11",
            Level.WARN,
            f"acknowledged_warnings 에 '{rule}' 이 있지만 그 경고가 나오지 않는다 - "
            "조건이 바뀌었으면 지운다",
        )
        for rule in sorted(stale)
    )
    return kept


def _signatures(source: str) -> list[str]:
    tree = ast.parse(source)
    sigs: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = [a.arg for a in node.args.args]
            sigs.append(f"{node.name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef):
            sigs.append(f"class {node.name}")
    return sigs


@dataclass(frozen=True, slots=True)
class CorpusReport:
    """코퍼스 전체 검증 결과."""

    checked: int
    load_errors: tuple[tuple[str, str], ...]
    violations: tuple[tuple[str, Violation], ...]

    @property
    def error_count(self) -> int:
        return len(self.load_errors) + sum(
            1 for _, v in self.violations if v.level is Level.ERROR
        )

    @property
    def warn_count(self) -> int:
        return sum(1 for _, v in self.violations if v.level is Level.WARN)

    @property
    def valid_count(self) -> int:
        bad = {name for name, _ in self.load_errors}
        bad |= {name for name, v in self.violations if v.level is Level.ERROR}
        return self.checked - len(bad)

    @property
    def ok(self) -> bool:
        return self.error_count == 0


def validate_corpus(root: Path) -> CorpusReport:
    """corpus/decoys/ 전체를 검증한다. `_` 로 시작하는 디렉터리는 건너뛴다."""
    load_errors: list[tuple[str, str]] = []
    violations: list[tuple[str, Violation]] = []
    checked = 0

    if not root.is_dir():
        return CorpusReport(checked=0, load_errors=(), violations=())

    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name.startswith("_"):
            continue
        checked += 1
        try:
            rec = load_decoy(d)
        except DecoyLoadError as exc:
            load_errors.append((d.name, str(exc)))
            continue
        violations.extend((d.name, v) for v in validate_decoy(rec))

    return CorpusReport(
        checked=checked,
        load_errors=tuple(load_errors),
        violations=tuple(violations),
    )
