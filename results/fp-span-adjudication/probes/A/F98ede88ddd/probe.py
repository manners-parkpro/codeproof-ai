"""D037 - delete=True · delete_on_close=False 인 임시 파일을 옮긴 뒤 문맥을 빠져나갈 때 FileNotFoundError 가 나는가.

네트워크 · 외부 프로그램 없음. 쓰기는 이 폴더 아래 임시 디렉터리에만 한다.
"""

import importlib.util
import inspect
import pathlib
import sys
import tempfile
import warnings

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d037_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


print("python", sys.version.split()[0])
closer_src = inspect.getsource(tempfile._TemporaryFileCloser)
print("tempfile cleanup swallows FileNotFoundError:", "except FileNotFoundError" in closer_src)
mod = load()
errors: list[str] = []
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        target = pathlib.Path(tmp) / "config.toml"
        for i in range(5):
            for fn in (mod._write, mod.save):  # 지적은 「성공한 쓰기마다」 - 직접 _write 와 save 둘 다
                try:
                    fn(target, f"v{i}\n")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{fn.__name__}: {type(exc).__name__}: {exc}")
        if target.exists():  # 3.12 전에는 delete_on_close 가 없어 모든 호출이 TypeError 라 대상이 생기지 않는다
            target.chmod(0o640)
            mod.save(target, "final\n")
            print("content:", repr(target.read_text(encoding="utf-8")), "| mode kept:", oct(target.stat().st_mode & 0o777))
        print("leftover files:", sorted(p.name for p in pathlib.Path(tmp).iterdir()))
print("exceptions raised:", len(errors), sorted(set(errors))[:3])
print("warnings:", [str(w.message) for w in caught])
