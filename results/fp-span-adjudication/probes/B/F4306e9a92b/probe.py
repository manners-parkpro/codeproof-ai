"""F4306e9a92b / F98e168cc07 / F98ede88ddd (D037) - 옮긴 임시 파일을 문맥 종료가 다시 지우려다 FileNotFoundError 로 실패하는가.

지적: delete=True · delete_on_close=False 라 문맥 종료에서 지우는데, 그 전에 replace 로 옮겼으므로
성공한 저장마다 FileNotFoundError 가 난다. 작업 폴더 안의 임시 디렉터리에서만 쓴다.
"""

import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = HERE.name


def _load():
    spec = importlib.util.spec_from_file_location(f"decoy_{TAG}", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
print("python", sys.version.split()[0])
with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    target = Path(tmp) / "config.toml"
    for n, body in enumerate(("a = 1\n", "a = 2\n", "a = 3\n"), 1):
        try:
            mod.save(target, body)  # 첫 회는 대상이 없고 둘째부터는 있다
            print(f"save #{n}: ok | content={target.read_text(encoding='utf-8')!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"save #{n}: {type(exc).__name__} {exc}")
    print("directory after saves:", sorted(p.name for p in Path(tmp).iterdir()))

    # _write 를 직접 불러도 같은가 (save 의 재시도가 OSError 를 덮지 않는 경로)
    try:
        mod._write(target, "direct\n")
        print("_write direct: ok |", repr(target.read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001
        print("_write direct:", type(exc).__name__, exc)
