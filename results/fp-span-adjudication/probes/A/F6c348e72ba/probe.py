"""F6c348e72ba (D022) - 몫의 언더플로가 표현 가능한 기여를 지우는가, 그리고 주장이 그것을 말하는가.

네트워크 · 외부 프로그램 · 쓰기 없음 (meta.toml 은 읽기만 한다).
"""

import importlib.util
import pathlib
import sys
import tomllib
from fractions import Fraction

HERE = pathlib.Path(__file__).resolve().parent
META = pathlib.Path("<repo>/corpus/decoys/D022-validated-nonzero-divisor/meta.toml")


def load(name: str = "d022_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
for values, weights in (([0.0, 1e308], [1e300, 1e-30]), ([1.0, 1e300], [1.0, 1e-310])):
    got = mod.average(values, weights)
    exact = sum(Fraction(v) * Fraction(w) for v, w in zip(values, weights)) / sum(Fraction(w) for w in weights)
    naive = sum(v * w for v, w in zip(values, weights)) / sum(weights)
    print(f"values={values} weights={weights} -> got {got!r} | exact {float(exact)!r} | naive {naive!r} | small share {weights[1] / max(weights)!r}")
claim = tomllib.loads(META.read_text(encoding="utf-8"))["safety"]["claim"]
print("claim excludes share underflow:", "몫의 언더플로" in claim)
