"""F53fa6aa582 (D079) - shuffled 가 내부 _tracks 를 제자리에서 섞어 순서를 바꾸는가 · 호출자의 리스트는 그대로인가."""

import importlib.util
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F53fa6aa582", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
tracks = [f"t{n}" for n in range(8)]
caller = list(tracks)
p = mod.Playlist(caller)
first = p.shuffled(random.Random(7))
print("caller list unchanged:", caller == tracks)
print("internal order after shuffled():", p._tracks, "| equals original:", p._tracks == tracks)
second = p.shuffled(random.Random(7))
print("same seed twice gives same result:", first == second, "| returned list is a copy:", first is not p._tracks)
