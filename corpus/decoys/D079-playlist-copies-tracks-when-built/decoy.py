"""재생 목록 - 만들 때 받은 곡 목록을 제 것으로 복사해 둔다."""

import random


class Playlist:
    def __init__(self, tracks: list[str]) -> None:
        self._tracks = list(tracks)

    def shuffled(self, rng: random.Random) -> list[str]:
        rng.shuffle(self._tracks)
        return list(self._tracks)
