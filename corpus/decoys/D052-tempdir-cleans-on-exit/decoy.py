"""내보내기 - 바깥이 작업 디렉터리를 치운다."""

from pathlib import Path
from tempfile import TemporaryDirectory


def _spill(workdir: Path, rows: list[str]) -> Path:
    part = workdir / "part-0.csv"
    part.write_text("\n".join(rows), encoding="utf-8")
    return part


def export(rows: list[str]) -> str:
    with TemporaryDirectory() as workdir:
        return _spill(Path(workdir), rows).read_text(encoding="utf-8")
