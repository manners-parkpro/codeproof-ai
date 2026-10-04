"""D122 변이 - 쓰는 단계 8개 · 쓰는 단계 점검 13개 · 독립 검토 5개 (약화 16 · 안전 10 · 경쟁 0) - 쓰는 단계 점검의 안전 둘을 약화로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

_BODY = (
    "    with _open_archive(target) as archive:\n"
    "        for name, data in entries:\n"
    "            archive.writestr(name, data)\n"
    "            count += 1\n"
    "    return count\n"
)
_IMPORT = "import zipfile\n"
_OPEN = '    return zipfile.ZipFile(target, "x")\n'
_WRITE = "            archive.writestr(name, data)\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[with] 문맥 없이 받음 (twin)": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    for name, data in entries:\n"
            "        archive.writestr(name, data)\n"
            "        count += 1\n"
            "    return count\n",
        ),
    ],
    "[성공 경로만] 끝에서만 close": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    for name, data in entries:\n"
            "        archive.writestr(name, data)\n"
            "        count += 1\n"
            "    archive.close()\n"
            "    return count\n",
        ),
    ],
    "[BaseException] except Exception 에서만 닫음": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    try:\n"
            "        for name, data in entries:\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    except Exception:\n"
            "        archive.close()\n"
            "        raise\n"
            "    archive.close()\n"
            "    return count\n",
        ),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[쓰기 예외] 항목을 꺼내는 next 만 감싸 닫음": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    items = iter(entries)\n"
            "    while True:\n"
            "        try:\n"
            "            name, data = next(items)\n"
            "        except StopIteration:\n"
            "            break\n"
            "        except BaseException:\n"
            "            archive.close()\n"
            "            raise\n"
            "        archive.writestr(name, data)\n"
            "        count += 1\n"
            "    archive.close()\n"
            "    return count\n",
        ),
    ],
    "[n=0] 하나라도 썼을 때만 닫음": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    try:\n"
            "        for name, data in entries:\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    finally:\n"
            "        if count:\n"
            "            archive.close()\n"
            "    archive.close()\n"
            "    return count\n",
        ),
    ],
    "[항목 종류] 데이터가 빈 항목은 건너뜀": [(_WRITE, "            if data:\n                archive.writestr(name, data)\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[반복자] 반복자를 with 밖에서 먼저 만듦": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    items = iter(entries)\n"
            "    with archive:\n"
            "        for name, data in items:\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    return count\n",
        ),
    ],
    "[핸들] 따로 연 핸들에 얹고 핸들은 정상 경로에서만 닫음": [
        (
            _BODY,
            '    handle = open(target, "xb")  # noqa: SIM115\n'
            '    with zipfile.ZipFile(handle, "w") as archive:\n'
            "        for name, data in entries:\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    handle.close()\n"
            "    return count\n",
        ),
    ],
    "[덮어쓰기] w 모드로 지난 백업을 자름": [(_OPEN, '    return zipfile.ZipFile(target, "w")\n')],
    "[덮어쓰기] a 모드로 지난 내용에 덧붙임": [(_OPEN, '    return zipfile.ZipFile(target, "a")\n')],
    "[항목마다 새로 엶] 루프 안의 with 가 매번 덮어씀": [
        (
            _BODY,
            "    for name, data in entries:\n"
            "        with _open_archive(target) as archive:\n"
            "            archive.writestr(name, data)\n"
            "        count += 1\n"
            "    return count\n",
        ),
    ],
    # 독립 검토 - 주장 오라클로는 약화인 「안전」 둘 · 같은 이름 항목 · 루프만 with 밖
    "[모두 담음] Exception 을 삼키고 개수를 돌려줌 - 담을 수 없는 이름 뒤 항목을 버리고 정상 반환 (독립 검토 · 쓰는 단계의 안전에서 옮김)": [
        (
            _BODY,
            "    with _open_archive(target) as archive:\n"
            "        try:\n"
            "            for name, data in entries:\n"
            "                archive.writestr(name, data)\n"
            "                count += 1\n"
            "        except Exception:  # noqa: BLE001, S110\n"
            "            pass\n"
            "    return count\n",
        ),
    ],
    "[거절] 첫 항목을 받을 때 엶 - 빈 entries 면 이미 있는 target 을 거절하지 않음 (독립 검토 · 쓰는 단계의 안전에서 옮김)": [
        (
            _BODY,
            "    archive = None\n"
            "    try:\n"
            "        for name, data in entries:\n"
            "            if archive is None:\n"
            "                archive = _open_archive(target)\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    finally:\n"
            "        if archive is not None:\n"
            "            archive.close()\n"
            "    return count\n",
        ),
    ],
    "[모두 담음] 이미 쓴 이름은 건너뜀": [(_WRITE, "            if name in archive.namelist():\n                continue\n" + _WRITE)],
    "[with] 항목 루프만 with 밖": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    for name, data in entries:\n"
            "        archive.writestr(name, data)\n"
            "        count += 1\n"
            "    with archive:\n"
            "        pass\n"
            "    return count\n",
        ),
    ],
    "[모두 담음] dict 로 모아 같은 이름은 마지막 것만 씀": [("        for name, data in entries:\n", "        for name, data in dict(entries).items():\n")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "예외를 RuntimeError 로 감싸 다시 던짐 (안전)": [
        (
            _BODY,
            "    try:\n"
            "        with _open_archive(target) as archive:\n"
            "            for name, data in entries:\n"
            "                archive.writestr(name, data)\n"
            "                count += 1\n"
            "    except Exception as exc:\n"
            '        raise RuntimeError("백업 실패") from exc\n'
            "    return count\n",
        ),
    ],
    "도우미 없이 ZipFile 을 바로 with (안전)": [
        ("    with _open_archive(target) as archive:\n", '    with zipfile.ZipFile(target, "x") as archive:\n'),
    ],
    "ZIP_DEFLATED 로 엶 (안전)": [(_OPEN, '    return zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED)\n')],
    "writestr 대신 open(name, w) 스트림 (안전)": [
        (_WRITE, '            with archive.open(name, "w") as dest:\n                dest.write(data)\n'),
    ],
    "try/finally 로 닫음 (안전)": [
        (
            _BODY,
            "    archive = _open_archive(target)\n"
            "    try:\n"
            "        for name, data in entries:\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    finally:\n"
            "        archive.close()\n"
            "    return count\n",
        ),
    ],
    "contextlib.closing 으로 감쌈 (안전)": [
        (_IMPORT, "import contextlib\nimport zipfile\n"),
        ("    with _open_archive(target) as archive:\n", "    with contextlib.closing(_open_archive(target)) as archive:\n"),
    ],
    "ExitStack 에 등록 (안전)": [
        (_IMPORT, "import contextlib\nimport zipfile\n"),
        (
            _BODY,
            "    with contextlib.ExitStack() as stack:\n"
            "        archive = stack.enter_context(_open_archive(target))\n"
            "        for name, data in entries:\n"
            "            archive.writestr(name, data)\n"
            "            count += 1\n"
            "    return count\n",
        ),
    ],
    "도우미가 with 를 품은 생성기 문맥 관리자 (안전)": [
        (_IMPORT, "import contextlib\nimport zipfile\n"),
        ("from collections.abc import Iterable\n", "from collections.abc import Iterable, Iterator\n"),
        (
            'def _open_archive(target: Path) -> zipfile.ZipFile:\n    return zipfile.ZipFile(target, "x")\n',
            "@contextlib.contextmanager\n"
            "def _open_archive(target: Path) -> Iterator[zipfile.ZipFile]:\n"
            '    with zipfile.ZipFile(target, "x") as archive:\n'
            "        yield archive\n",
        ),
    ],
    # 독립 검토 - 「그때까지 쓴 항목」 은 받은 항목이 아니라 쓴 항목이다
    "entries 를 열기 전에 list 로 다 읽음 (안전)": [(_BODY, "    items = list(entries)\n" + _BODY.replace("for name, data in entries:", "for name, data in items:"))],
    "연 뒤에 entries 를 list 로 다 읽음 (안전)": [
        (_BODY, _BODY.replace("        for name, data in entries:\n", "        items = list(entries)\n        for name, data in items:\n")),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
