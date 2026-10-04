"""D149 반증 - 임시 파일의 deliveries 에 같은 message_id 를 매번 다른 body 로 세 번씩 넣고, 비슷하지만 다른 message_id 와
실패한 부름을 섞어 줄과 body 를 본다. 정규화만 다른 id · 같은 body 의 다른 id · 다시 배달 사이에 낀 다른 id · 하위 타입 id 를
더 치고, UTF-8 이 아닌 파일은 거절하는지 본다."""

from __future__ import annotations

import enum
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

# 비슷하지만 다른 message_id - 대소문자 · 뒤 공백 · 숫자처럼 보이는 문자열 · NUL 뒤만 다른 것 · LIKE 의 와일드카드 ·
# 빈 문자열 · 비문자. 차례에 뜻이 있다 - 와일드카드가 든 것은 그것과 맞는 것보다 뒤에 온다.
_NUL = chr(0)
_IDS = ("m1", "M1", "m1 ", "1", "001", "1.0", f"a{_NUL}b", f"a{_NUL}c", "a", "mx1", "m_1", "%", "", chr(0xFFFE), "메시지-7")
_BROKEN = "깨진" + chr(0xD800)  # UTF-8 로 못 바꿔 바인딩에서 실패한다


class _Kind(str, enum.Enum):
    """표준 라이브러리가 끼운 메서드만 가진 (str, Enum) 혼합형 - 값이 같은 문자열이면 같은 message_id 다."""

    SAME = "m1"
    NEW = "enum-1"


class _Sub(str):
    """메서드를 재정의하지 않은 str 하위 클래스."""


def _rows(path: Path) -> Counter[tuple[object, object]]:
    with closing(sqlite3.connect(path)) as conn:
        try:
            return Counter(conn.execute("SELECT message_id, body FROM deliveries").fetchall())
        except sqlite3.OperationalError:  # 표가 아직 없다
            return Counter()


def _writable(text: str) -> bool:
    try:
        str.__str__(text).encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _play(mod: ModuleType, path: Path, script: list[tuple[str, str]]) -> bool:
    """부름마다 줄을 새 연결로 읽어 기대와 견준다 - 기대는 message_id 마다 처음 예외 없이 끝난 부름의 body 로 한 줄이다."""
    first: dict[str, str] = {}
    for mid, body in script:
        try:
            mod.record(str(path), mid, body)
        except Exception:  # noqa: BLE001 - 실패한 부름은 줄을 남기지 않아야 한다
            if _writable(mid) and _writable(body):
                return True  # UTF-8 로 쓸 수 있는 부름은 예외 없이 끝나야 한다
        else:
            first.setdefault(str.__str__(mid), str.__str__(body))
        if _rows(path) != Counter(first.items()):
            return True
    return False


def _rounds() -> list[tuple[str, str]]:
    script: list[tuple[str, str]] = []
    for rnd in range(3):
        for n, mid in enumerate(_IDS):
            if n % 3 == rnd:
                script.append((mid, _BROKEN))
            script.append((mid, f"{rnd}-{n}"))
    return script


def _story() -> list[tuple[str, str]]:
    script = [(chr(0xE9), "n1"), ("e" + chr(0x301), "n2"), ("m1", "k1"), (chr(0xFF4D) + chr(0xFF11), "k2")]  # 정규화만 다른 id
    script += [("dup-a", "same"), ("dup-b", "same")]  # 같은 body 의 다른 id
    script += [("w", "w0"), *((f"f{i}", "f") for i in range(40)), ("w", "w1")]  # 다시 배달 사이에 낀 다른 id 40개
    script += [(_Kind.SAME, "e1"), (_Kind.NEW, "e2"), ("enum-1", "e3"), (_Sub("s-1"), "s1"), ("s-1", "s2"), ("b-enum", _Kind.NEW)]
    script += [("L" * 300 + "-1", "l1"), ("L" * 300 + "-2", "l2"), ("L" * 300 + "-1", "l3")]  # 앞부분이 같은 긴 id
    script += [("ab", "c1"), ("a" + chr(0x200B) + "b", "c2"), (chr(0xFEFF) + "ab", "c3")]  # 서식 문자(Cf)만 다른 id
    return script


def attack(mod: ModuleType) -> bool:
    """줄이 기대와 하나라도 다르거나, UTF-8 이 아닌 파일에 쓰면 True.

    🔴 같은 message_id 를 세 번 · 매번 다른 body 로 넣는다 - 늘지도 바뀌지도 않아야 한다.
    🔴 비슷하지만 다른 message_id 를 섞는다 - 같은 것으로 치면 둘째가 빠진다. 정규화만 다른 id(é 두 꼴 · 전각)도 다르다.
    🔴 실패한 부름(서로게이트가 든 body)을 첫 부름 앞뒤에 섞는다 - 줄을 남기지 않아야 하고, 그 뒤의 정상 부름이
       처음 body 가 된다. 예외 없이 끝나면 그 body 가 기대가 된다 (주장 그대로).
    🔴 같음은 message_id 로만 정한다 - 같은 body 의 다른 id 는 각자 한 줄이고, 다시 배달 사이에 다른 id 가 많이 껴도 그대로다.
    🔴 하위 타입 id 와 body((str, Enum) · str 하위 클래스)는 그 문자열 값으로 담긴다 - str() 로 바꾸면 혼합형은 이름이 된다.
    🔴 UTF-8 이 아닌 이미 있는 파일(다른 표가 있는 UTF-16le · UTF-16be)에는 아무것도 쓰지 않고 거절한다 - 비문자가
       U+FFFD 로 바뀌어 다른 id 가 같아진다.
    🔴 id 는 그대로 담긴다 - 앞부분이 같은 300자 id 와 서식 문자(Cf)만 다른 id 를 섞는다 (자르거나 서식 문자를 지우는 판 ·
       6라운드 검토).
    🔴 UTF-8 로 쓸 수 있는 부름은 예외 없이 끝나야 한다 - 늘 거절하거나 새 파일을 UTF-16 으로 만드는 판이 「줄 없음」으로 공허하게
       통과하지 않게.
    🔴 줄은 부름마다 새 연결로 읽는다 - 커밋되지 않은 줄을 세지 않게.
    🔴 다른 표와 색인이 이미 있는 UTF-8 파일에도 쓴다 - 그런 파일을 거절하는 판 (세 번째 렌즈 · 주장은 deliveries 와
       deliveries_message_id 만 record 의 것으로 둔다).

    decoy 는 _RECORD 가 같은 message_id 가 없을 때만 넣는다.
    twin 은 매번 넣어 다시 배달된 메시지가 줄을 늘린다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if _play(mod, root / "rounds.db", _rounds()) or _play(mod, root / "story.db", _story()):
            return True
        other = root / "other.db"  # 다른 표와 색인이 이미 있는 UTF-8 파일 - 주장의 「없거나 UTF-8」 안이다
        with closing(sqlite3.connect(other)) as conn:
            conn.execute("CREATE TABLE settings (k TEXT)")
            conn.execute("CREATE INDEX settings_k ON settings (k)")
            conn.commit()
        if _play(mod, other, _rounds()[:12]):
            return True
        for encoding in ("UTF-16le", "UTF-16be"):  # UTF-8 이 아닌 꼴 둘 다 - 하나만 거절하는 판
            u16 = root / f"{encoding}.db"
            with closing(sqlite3.connect(u16)) as conn:
                conn.execute(f"PRAGMA encoding = '{encoding}'")
                conn.execute("CREATE TABLE settings (k TEXT)")
                conn.commit()
            for mid in ("a", chr(0xFFFE), chr(0xFFFF)):
                try:
                    mod.record(str(u16), mid, "x")
                except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                    continue
                return True
            if _rows(u16):
                return True
    return False
