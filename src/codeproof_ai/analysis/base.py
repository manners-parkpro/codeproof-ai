"""정적분석 확장점.

🔴 이 모듈에 Python 전용 개념이 새어 들어가면 Java 확장 약속이 깨진다
   (CLAUDE.md A3). `.py` 확장자, ast 노드 타입, ruff 룰 코드를 여기 두지 않는다.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.run import ToolVersion
    from codeproof_ai.domain.target import ReviewTarget


@contextmanager
def materialize(target: ReviewTarget) -> Iterator[Path]:
    """ReviewTarget 을 임시 디렉터리에 복원한다.

    🔴 공정성 장치다. 분석기를 실제 레포에 돌리면 모델보다 **더 많은 맥락**
       (주변 파일·설정·타입 스텁)을 얻어서 같은 과제를 푸는 게 아니게 된다.
       분석기는 `target.files` 에 있는 것만 본다 - 모델과 정확히 같은 가시 범위다.
    """
    with tempfile.TemporaryDirectory(prefix="codeproof-") as tmp:
        root = Path(tmp)
        for f in target.files:
            dest = root / f.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.content, encoding="utf-8")
        yield root


@contextmanager
def materialize_many(
    targets: Sequence[ReviewTarget],
    *,
    as_packages: bool = False,
) -> Iterator[tuple[Path, dict[str, str]]]:
    """대상 여러 개를 각각 별도 하위 디렉터리에 복원한다.

    🔴 두 가지를 해야 mypy 일괄 실행이 된다:

       ① 디렉터리명을 **유효한 파이썬 식별자로 소독**한다.
          sample_id 에 하이픈과 `#` 이 있으면 모듈명이 될 수 없다.
       ② `as_packages=True` 면 각 상자에 **`__init__.py` 를 둔다.**
          [실측] ① 만으로는 부족했다 - 상자가 패키지가 아니면 그 안의 decoy.py 들이
          전부 `decoy` 모듈이 되어 `Duplicate module named "decoy"` 가 난다.
          패키지가 되면 `s0000.decoy` · `s0001.decoy` 로 갈린다.

    🔴 `as_packages` 를 필요한 분석기만 켜는 이유: **복원 방식이 분석 결과를
       바꾸면 안 된다.** [실측] `__init__.py` 를 무조건 넣었더니 Ruff 의
       `INP001`(암묵적 네임스페이스 패키지) 지적이 사라져 일괄과 개별이
       **다른 숫자**를 냈다. mypy 는 모듈명 해소에 필요하고 Ruff 는 아니다.

    Yields:
        (루트, 디렉터리명 -> target_id 매핑)
    """
    with tempfile.TemporaryDirectory(prefix="codeproof-batch-") as tmp:
        root = Path(tmp)
        mapping: dict[str, str] = {}
        for i, target in enumerate(targets):
            slug = f"s{i:04d}"
            mapping[slug] = target.target_id
            box = root / slug
            box.mkdir()
            if as_packages:
                (box / "__init__.py").touch()
            for f in target.files:
                dest = box / f.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(f.content, encoding="utf-8")
        yield root, mapping


def split_batch_path(root: Path, filename: str) -> tuple[str, str] | None:
    """일괄 실행 결과의 파일 경로를 (디렉터리 슬러그, 대상 상대경로) 로 나눈다."""
    try:
        rel = Path(filename).resolve().relative_to(root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:  # noqa: PLR2004
        return None
    return parts[0], str(Path(*parts[1:]))


def analyze_batch(
    targets: Sequence[ReviewTarget],
    run: Callable[[Path], list[dict[str, Any]]],
    to_findings: Callable[[list[dict[str, Any]], ReviewTarget], list[Finding]],
    *,
    path_key: str,
    as_packages: bool = False,
) -> dict[str, list[Finding]]:
    """대상 전부를 상자별로 복원해 `run` **한 번**으로 분석하고, 보고 경로로 대상을 되찾는다.

    `path_key` 는 도구 레코드의 파일 경로 칸이다 - 대상 상대경로로 바꿔 `to_findings` 에
    넘긴다. 상자로 되돌릴 수 없는 레코드는 버린다.
    """
    if not targets:
        return {}
    by_id = {t.target_id: t for t in targets}
    out: dict[str, list[Finding]] = {t.target_id: [] for t in targets}

    with materialize_many(targets, as_packages=as_packages) as (root, mapping):
        for rec in run(root):
            split = split_batch_path(root, str(rec.get(path_key, "")))
            if split is None:
                continue
            slug, rel = split
            tid = mapping.get(slug)
            if tid is None:
                continue
            out[tid].extend(to_findings([{**rec, path_key: rel}], by_id[tid]))
    return out


@runtime_checkable
class Analyzer(Protocol):
    """한 가지 정적분석 도구를 감싼다.

    구현체는 도구 원본 출력을 domain.Finding 으로 정규화할 책임을 진다.
    특히 **컬럼 규약 변환은 구현체 안에서만** 한다 (B1) -
    어댑터 하나가 변환 하나를 책임진다.
    """

    name: str
    """도구 식별자. Finding.source 에 그대로 들어간다."""

    language: str
    """대상 언어. registry 가 이걸로 고른다."""

    def version(self) -> ToolVersion:
        """도구 버전. RunManifest 에 기록된다.

        ruff 는 pre-1.0 이라 JSON 스키마가 바뀐다 - 정확히 핀해야 한다.
        """
        ...

    def config_signature(self) -> str:
        """🔴 이 실행의 설정 지문. 매니페스트에 실린다.

        룰 선택은 측정 손잡이다 - `--select ALL` 과 `--select E,F` 는
        같은 코드에서 FP 수가 완전히 다르다. 기록하지 않으면 재현 불가다.
        """
        ...

    def analyze_many(
        self, targets: Sequence[ReviewTarget]
    ) -> dict[str, list[Finding]]:
        """여러 대상을 **한 번의 subprocess** 로 분석한다.

        [실측] mypy 는 파일 1개든 30개든 ~113ms 로 같다. 대상마다 따로 띄우면
        300 샘플에 37초, 한 번에 돌리면 1초다.

        구현하지 않으면 analyze() 를 반복하는 기본 구현이 쓰인다 -
        느리지만 정확성은 같다.
        """
        ...

    def analyze(self, target: ReviewTarget) -> list[Finding]:
        """리뷰 대상을 분석한다.

        구현 규약:
        - `materialize(target)` 안에서 돈다. 실제 레포를 보지 않는다.
        - 진단 1건 파싱이 깨져도 **예외를 올리지 않는다.** 나머지를 살린다.
          도구 자체가 죽은 경우만 올린다.
        - 종료 코드로 판단하지 않는다. 파싱된 페이로드로 판단한다.
        - 원본 페이로드를 Finding.raw 에 보존한다.
        """
        ...


@runtime_checkable
class SymbolIndex(Protocol):
    """위치 → 둘러싼 심볼 해석기. 언어별 구현.

    Finding 에 `enclosing` 을 채우는 것이 이 플랫폼의 실질적 차별점이다 -
    Ruff 도 mypy 도 이 정보를 내지 않는다. SARIF logicalLocations 로도 나간다.
    """

    language: str

    def enclosing_symbol(self, source: str, line: int) -> tuple[str | None, str | None]:
        """(정규화 이름, 종류) 를 반환한다. 최상위면 (None, None).

        🔴 데코레이터 줄을 포함해야 한다 (B3) -
           FunctionDef.lineno 는 `def` 를 가리키고 데코레이터는 그 앞이다.
        """
        ...
