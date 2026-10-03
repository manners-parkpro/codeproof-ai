"""리뷰 대상 — 런타임이 보는 전부.

🔴 이 타입에는 정답 라벨이 없다. 있을 수 없다.
   라벨이 붙은 형태는 eval/sample.py 의 LabeledSample 이고, eval/ 안에만 존재한다.
   런타임(analysis·llm·verify)은 eval/ 을 import 할 수 없으므로
   라벨을 볼 **방법 자체가 없다** - 테스트로 단속하는 게 아니라 구조로 막는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SourceFile:
    """리뷰어에게 제시되는 파일 하나."""

    path: str
    content: str

    @property
    def line_count(self) -> int:
        return len(self.content.splitlines())


@dataclass(frozen=True, slots=True)
class ReviewTarget:
    """리뷰 1건의 입력.

    `files` 가 **리뷰어가 볼 수 있는 전부**다. 이게 이 타입의 핵심 의미다.

    모델 API 비교에는 툴도 파일 접근도 없으므로, 여기 없는 코드는
    리뷰어에게 존재하지 않는 것과 같다. D층 decoy 의 V4 규칙
    (가드가 decoy.py 안에서 보여야 한다) 이 바로 이 불변식의 다른 표현이다.

    Attributes:
        target_id: 안정 식별자.
        files: 제시되는 소스. decoy 는 파일 그 자체, PR 은 변경된 파일들.
        diff: PR 리뷰면 변경분. 파일 단위 리뷰면 None.
            🔴 diff 를 필수로 두지 않는다 - decoy 를 가짜 diff 로 감싸면
               "무엇이 보이는가" 라는 의미가 흐려진다.
        repo: 원본 저장소. 소스는 번들하지 않고 여기로 되짚는다 (K1).
        commit_sha: 정확한 커밋.
    """

    target_id: str
    files: tuple[SourceFile, ...]
    diff: str | None = None
    repo: str | None = None
    commit_sha: str | None = None
    _index: dict[str, SourceFile] = field(
        init=False, repr=False, compare=False, hash=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.files:
            msg = f"{self.target_id}: 제시할 파일이 없으면 리뷰 대상이 아니다"
            raise ValueError(msg)
        seen = [f.path for f in self.files]
        if len(set(seen)) != len(seen):
            msg = f"{self.target_id}: 경로가 중복된다 - {seen}"
            raise ValueError(msg)
        self._index.update({f.path: f for f in self.files})

    def file(self, path: str) -> SourceFile | None:
        """제시된 파일을 찾는다. 없으면 None - 리뷰어에게도 없는 파일이다."""
        return self._index.get(path)

    def match_file(self, reported: str) -> SourceFile | None:
        """도구가 보고한 경로의 끝이 맞는 첫 제시 파일. 없으면 None.

        분석기는 복원한 임시 디렉터리의 절대경로를 보고하므로 경로 끝으로 되찾는다.
        """
        return next((f for f in self.files if reported.endswith(f.path)), None)

    def is_visible(self, path: str, line: int) -> bool:
        """그 위치가 리뷰어에게 실제로 보이는가.

        지적이 보이지 않는 곳을 가리키면 그건 환각이거나 매칭 오류다.
        """
        f = self._index.get(path)
        return f is not None and 1 <= line <= f.line_count

    @property
    def visible_paths(self) -> tuple[str, ...]:
        return tuple(f.path for f in self.files)
