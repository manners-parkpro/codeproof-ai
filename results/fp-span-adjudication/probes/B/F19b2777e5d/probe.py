"""F19b2777e5d (D043) - candidate 는 resolve 하고 _ROOT 는 하지 않는 차이가 무엇을 만드는가.

(1) 지금 환경 (_ROOT = /srv/data 가 없거나 링크가 아님) 에서 정상 이름 · 탈출 이름
(2) _ROOT 가 링크인 환경 - /srv/data 를 만들 권한이 없으므로, 작업 폴더 안에 링크 루트를 만들고 decoy 의
    resolve_entry 와 _under_root 가 쓰는 표현식을 그대로 그 루트에 건다 (모듈 상수를 바꾸면 monkeypatch 라
    위협 모델 밖이므로 쓰지 않는다). 그리고 밖을 가리키는 경로가 통과하는지도 본다.
"""

import importlib.util
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F19b2777e5d", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
print("_ROOT:", mod._ROOT, "| exists:", mod._ROOT.exists(), "| is_symlink:", mod._ROOT.is_symlink())
for name in ("report.csv", "sub/x.txt", "../../etc/passwd", "..", "a/../../../secret"):
    try:
        print(f"resolve_entry({name!r}) ->", mod.resolve_entry(name))
    except ValueError as exc:
        print(f"resolve_entry({name!r}) -> ValueError", exc)

with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    real = Path(tmp) / "real-data"
    real.mkdir()
    (real / "report.csv").write_text("x")
    (Path(tmp) / "outside.txt").write_text("secret")
    root = Path(tmp) / "srv-data"  # 링크인 루트
    os.symlink(real, root)

    def same_check(name):
        candidate = (root / name).resolve()  # resolve_entry 의 13행
        ok = candidate.is_relative_to(root)  # _under_root 의 9행
        return candidate, ok

    for name in ("report.csv", "new.txt", "../outside.txt", "../srv-data/report.csv", "../real-data/report.csv"):
        candidate, ok = same_check(name)
        inside = candidate.is_relative_to(real.resolve())
        print(f"symlinked root: {name!r} -> accepted={ok} | really inside root={inside}")
