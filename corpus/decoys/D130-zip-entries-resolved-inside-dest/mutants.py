"""D130 변이 - 쓰는 단계 11개 · 쓰는 단계 점검 19개 · 독립 검토 3개 (약화 20 · 안전 13 · 경쟁 0) - 주장을 안전 하나로 좁혀 쓰는 단계의 약화 하나를 안전으로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

_RESOLVE = "            target = (root / info.filename).resolve()\n"
_TEST = "            if not target.is_relative_to(root):\n"
_RAISE = '                raise ValueError(f"대상 폴더 밖으로 풀리는 항목: {info.filename!r}")\n'
_CHECK = _TEST + _RAISE
_MKDIR = "            target.parent.mkdir(parents=True, exist_ok=True)\n"
_UNLINK = "            target.unlink(missing_ok=True)\n"
_READ = "            data = zf.read(info)\n"
_PUT = "            target.write_bytes(data)\n"
_WRITE = _READ + _MKDIR + _UNLINK + _PUT
_LOOP = "        for info in members:\n" + _RESOLVE + _CHECK + _WRITE + "            written.append(target)\n"
_IMPORT = "import zipfile\n"


def _only(index: int) -> list[tuple[str, str]]:
    """묶음에서 한 자리의 항목만 확인하는 변이 - 0 은 첫 항목, -1 은 마지막 항목."""
    return [(
        _LOOP,
        "        targets = [(info, (root / info.filename).resolve()) for info in members]\n"
        f"        if targets and not targets[{index}][1].is_relative_to(root):\n"
        f'            raise ValueError(f"대상 폴더 밖으로 풀리는 항목: {{targets[{index}][0].filename!r}}")\n'
        "        for info, target in targets:\n" + _WRITE + "            written.append(target)\n",
    )]


WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[검사] is_relative_to 검사를 뺌 (twin)": [(_CHECK, "")],
    "[검사] resolve 없이 문자열 접두사로": [
        (_RESOLVE + _TEST, "            target = root / info.filename\n            if not str(target).startswith(str(root)):\n"),
    ],
    "[검사] normpath 로만 정규화 - 심볼릭 링크를 못 봄": [
        (_IMPORT, "import os\nimport zipfile\n"),
        (_RESOLVE, "            target = Path(os.path.normpath(root / info.filename))\n"),
    ],
    "[검사] 이름의 .. 만 거름": [
        (_RESOLVE + _CHECK, '            if ".." in Path(info.filename).parts:\n' + _RAISE + "            target = root / info.filename\n"),
    ],
    "[검사] 쓴 뒤에 확인": [(_CHECK + _WRITE, _WRITE + _CHECK)],
    "[검사] ZipFile.extract 에 맡김": [
        (_RESOLVE + _CHECK + _WRITE + "            written.append(target)\n", "            written.append(Path(zf.extract(info, root)))\n"),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화 (새 파일만 세고 · 밖 항목이 한 자리뿐이고 · 형제 폴더가 없었다)
    "[검사] resolve 뒤 문자열 접두사로 비교 - 이름 앞부분이 같은 형제 폴더": [(_TEST, "            if not str(target).startswith(str(root)):\n")],
    "[검사] 쓴 뒤 확인하고 밖이면 지움 - 밖의 기존 파일이 사라짐": [
        (_CHECK + _WRITE, _WRITE + _TEST + "                target.unlink()\n" + _RAISE),
    ],
    "[검사] 검사 전에 부모 디렉터리를 만듦 - 밖에 디렉터리가 생김": [(_CHECK + _READ + _MKDIR, _MKDIR + _CHECK + _READ)],
    "[항목 수] 첫 항목만 확인": _only(0),
    "[항목 수] 마지막 항목만 확인": _only(-1),
    "[절대 경로] 검사는 앞 / 를 뗀 이름으로, 쓰기는 원래 이름으로": [
        (_TEST, '            if not (root / info.filename.lstrip("/")).resolve().is_relative_to(root):\n'),
    ],
    "[링크 뒤 ..] normpath 한 뒤 resolve 로 확인하고 원래 이름으로 씀": [
        (_IMPORT, "import os\nimport zipfile\n"),
        (_RESOLVE + _TEST, "            target = root / info.filename\n            if not Path(os.path.normpath(target)).resolve().is_relative_to(root):\n"),
    ],
    "[하드 링크] 기존 파일을 끊지 않고 그 자리에 씀 (쓰는 단계 점검 전 decoy)": [(_UNLINK, "")],
    # 축마다 그 축의 탐침으로만 잡히는 약화 - 탐침이 서로 겹쳐 위 약화들은 여러 축에 함께 잡힌다
    "[가운데 자리] 첫 항목과 마지막 항목만 확인": [(
        _LOOP,
        "        targets = [(info, (root / info.filename).resolve()) for info in members]\n"
        "        for info, target in targets[:1] + targets[-1:]:\n" + _CHECK
        + "        for info, target in targets:\n" + _WRITE + "            written.append(target)\n",
    )],
    "[마지막 성분 링크] 부모만 resolve 하고 하드 링크일 때만 끊음": [
        (_RESOLVE, "            target = (root / info.filename).parent.resolve() / Path(info.filename).name\n"),
        (_UNLINK, "            if target.exists() and target.stat().st_nlink > 1:\n                target.unlink()\n"),
    ],
    "[밖의 기존 파일] 쓴 뒤 확인하고 밖이면 지움 - 부모 디렉터리는 확인 뒤에 만듦": [
        (_CHECK + _WRITE, _READ + _UNLINK + _PUT + _TEST + "                target.unlink()\n" + _RAISE + _MKDIR),
    ],
    # 독립 검토 - 적대 묶음에 디렉터리 항목(이름이 / 로 끝남)이 없었다
    "[디렉터리 항목] 확인 없이 mkdir": [
        ("        members = [info for info in zf.infolist() if not info.is_dir()]\n",
         "        for info in zf.infolist():\n            if info.is_dir():\n                (root / info.filename).mkdir(parents=True, exist_ok=True)\n"
         "        members = [info for info in zf.infolist() if not info.is_dir()]\n"),
    ],
    "[디렉터리 항목] resolve 한 경로로 확인 없이 mkdir": [
        ("        members = [info for info in zf.infolist() if not info.is_dir()]\n",
         "        for info in zf.infolist():\n            if info.is_dir():\n                (root / info.filename).resolve().mkdir(parents=True, exist_ok=True)\n"
         "        members = [info for info in zf.infolist() if not info.is_dir()]\n"),
    ],
    "[검사] dest 가 아니라 dest 의 부모 안인지 봄": [(_TEST, "            if not target.is_relative_to(root.parent):\n")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "os.path.commonpath 로 확인 (안전)": [
        (_IMPORT, "import os\nimport zipfile\n"),
        (_TEST, "            if os.path.commonpath([root, target]) != str(root):\n"),
    ],
    "relative_to 의 ValueError 로 확인 (안전)": [(_CHECK, "            target.relative_to(root)\n")],
    "copyfileobj 로 흘려 씀 (안전)": [
        (_IMPORT, "import shutil\nimport zipfile\n"),
        (_PUT, '            with zf.open(info) as src, target.open("wb") as out:\n                shutil.copyfileobj(src, out)\n'),
    ],
    "모두 확인한 뒤에 씀 (안전)": [
        (_LOOP, "        targets = []\n        for info in members:\n" + _RESOLVE + _CHECK + "            targets.append((info, target))\n"
                "        for info, target in targets:\n" + _WRITE + "            written.append(target)\n"),
    ],
    # 쓰는 단계 점검 - 주장은 안쪽 항목을 풀어 주는지 정하지 않는다 (밖을 건드리지 않는 거짓 거절은 안전하다)
    "dest 를 resolve 하지 않음 - 링크로 넘긴 dest 의 항목을 모두 거절 (안전)": [("    root = dest.resolve()\n", "    root = dest\n")],
    "밖이면 조용히 건너뜀 (안전)": [(_RAISE, "                continue\n")],
    "PermissionError 로 거절 (안전)": [(_RAISE, _RAISE.replace("ValueError", "PermissionError"))],
    "os.path.realpath 로 해석 (안전)": [
        (_IMPORT, "import os\nimport zipfile\n"),
        (_RESOLVE, "            target = Path(os.path.realpath(root / info.filename))\n"),
    ],
    "O_NOFOLLOW 로 열어 씀 (안전)": [
        (_IMPORT, "import os\nimport zipfile\n"),
        (_PUT, '            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)\n'
               '            with os.fdopen(fd, "wb") as out:\n                out.write(data)\n'),
    ],
    "부모 디렉터리만 resolve - 마지막 성분의 링크는 unlink 가 끊는다 (안전)": [
        (_RESOLVE, "            target = (root / info.filename).parent.resolve() / Path(info.filename).name\n"),
    ],
    "디렉터리 항목을 거르지 않음 - 다음 항목에서 멈출 뿐 (안전)": [
        ("        members = [info for info in zf.infolist() if not info.is_dir()]\n", "        members = zf.infolist()\n"),
    ],
    "절대 경로 이름은 모두 거절 (안전)": [
        (_RESOLVE, '            if info.filename.startswith("/"):\n' + _RAISE + _RESOLVE),
    ],
    "쓴 경로를 tuple 로 돌려줌 (안전)": [("    return written\n", "    return tuple(written)  # type: ignore[return-value]\n")],
}

RACY: dict[str, list[tuple[str, str]]] = {}
