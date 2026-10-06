"""F53fa6aa582 (D079) - shuffled 가 내부 사본의 순서를 바꾸는가, 그것이 밖에서 무엇으로 관측되는가, 쌍이 그것을 어떻게 말하는가.

네트워크 · 외부 프로그램 · 쓰기 없음 (meta.toml 은 읽기만 한다). _tracks 는 관찰만 한다.
"""

import importlib.util
import pathlib
import random
import sys
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
META = pathlib.Path("<repo>/corpus/decoys/D079-playlist-copies-tracks-when-built/meta.toml")


def load(name: str = "d079_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
original = [f"t{i:02d}" for i in range(10)]
tracks = list(original)
playlist = mod.Playlist(tracks)
first = playlist.shuffled(random.Random(7))
second = playlist.shuffled(random.Random(7))
print("caller list unchanged:", tracks == original)
print("internal order equals construction order:", playlist._tracks == original)
print("same seed, two calls, same order:", first == second)
print("returned list is not the internal list:", first is not playlist._tracks)
print("both results are permutations of the tracks:", sorted(first) == sorted(second) == original)
public = [n for n in dir(playlist) if not n.startswith("_")]
print("public members:", public)
justification = tomllib.loads(META.read_text(encoding="utf-8"))["safety"]["justification"]
print("justification states in-place shuffle of the private copy:", "제자리에서 섞는 대상은 재생 목록이 혼자 가진 사본" in justification)
