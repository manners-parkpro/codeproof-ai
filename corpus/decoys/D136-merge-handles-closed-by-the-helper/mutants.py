"""D136 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 23개 · 독립 검토 4개 · 교차 1개 (약화 30 · 안전 10 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_GUARD = (
    "    try:\n"
    "        yield handles\n"
    "    finally:\n"
    "        with contextlib.ExitStack() as stack:\n"
    "            for handle in handles:\n"
    "                stack.callback(handle.close)\n"
)
_MERGE = (
    "    with _all_closed() as handles:\n"
    "        for path in paths:\n"
    '            handles.append(open(path, encoding="utf-8"))\n'
    "        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n"
)
_WRITE = "        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[문맥] 닫는 문맥 없음 (twin)": [
        (_MERGE, "    handles: list[IO[str]] = []\n    for path in paths:\n        handles.append(open(path, encoding=\"utf-8\"))\n"
                 "    out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n"),
    ],
    "[문맥] 성공했을 때만 닫음 - finally 없음": [
        (_GUARD, "    yield handles\n    for handle in handles:\n        handle.close()\n"),
    ],
    "[닫기] 마지막 하나만 닫음": [(_GUARD, "    try:\n        yield handles\n    finally:\n        if handles:\n            handles.pop().close()\n")],
    "[열기] 문맥 밖에서 먼저 모두 엶 - 여는 도중 실패하면 앞의 것이 샘": [
        (_MERGE, '    opened = [open(path, encoding="utf-8") for path in paths]\n    with _all_closed() as handles:\n        handles.extend(opened)\n'
                 "        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n"),
    ],
    "[줄 끝] \\n 을 붙이지 않음": [('        yield line if line.endswith("\\n") else line + "\\n"\n', "        yield line\n")],
    "[차례] 합치지 않고 이어 붙임": [(_WRITE, "        out.writelines(itertools.chain(*(_lines(handle) for handle in handles)))\n"), ("import heapq\n", "import heapq\nimport itertools\n")],
    "[차례] 같은 줄을 하나로": [(_WRITE, "        out.writelines(sorted(set(heapq.merge(*(_lines(handle) for handle in handles)))))\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[예외] 아는 실패(OSError · 디코딩)만 정리 - 인코딩 못 하는 out · 닫힌 out · NUL 경로는 열린 채': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except (OSError, UnicodeDecodeError):\n        for handle in handles:\n            handle.close()\n        raise\n    for handle in handles:\n        handle.close()\n')],
    '[예외] 실패를 RuntimeError 로 바꿔 올림 - 그 예외가 아니라 다른 예외가 올라감': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except Exception as exc:\n        raise RuntimeError(f"합치기 실패: {exc}") from None\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n')],
    '[줄 끝] 번역 없이 열고 CRLF 만 바꿈 - 홀로 선 \\r 이 줄 끝으로 남음': [('            handles.append(open(path, encoding="utf-8"))\n', '            handles.append(open(path, encoding="utf-8", newline=""))\n'), ('        yield line if line.endswith("\\n") else line + "\\n"\n', '        line = line.replace("\\r\\n", "\\n")\n        yield line if line.endswith("\\n") else line + "\\n"\n')],
    '[차례] 대소문자를 무시하고 합침 (key=str.lower)': [('        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '        out.writelines(heapq.merge(*(_lines(handle) for handle in handles), key=str.lower))\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[줄 끝] 파일 전체를 읽고 끝에 \\n 이 없으면 붙인 뒤 나눔 - 빈 파일에서 빈 줄 하나가 나옴': [('    for line in handle:\n        yield line if line.endswith("\\n") else line + "\\n"\n', '    text = handle.read()\n    if not text.endswith("\\n"):\n        text += "\\n"\n    for line in text[:-1].split("\\n"):\n        yield line + "\\n"\n')],
    '[줄 끝] 줄 끝 번역 없이 엶 (newline="") - \\r\\n 이 그대로 나감': [('            handles.append(open(path, encoding="utf-8"))\n', '            handles.append(open(path, encoding="utf-8", newline=""))\n')],
    '[인코딩] ascii 로 엶 - UTF-8 의 비 ASCII 줄에서 실패': [('            handles.append(open(path, encoding="utf-8"))\n', '            handles.append(open(path, encoding="ascii"))\n')],
    '[차례] 파일 안에서 연속한 같은 줄을 하나로 (uniq)': [('    for line in handle:\n        yield line if line.endswith("\\n") else line + "\\n"\n', '    previous = None\n    for line in handle:\n        line = line if line.endswith("\\n") else line + "\\n"\n        if line != previous:\n            yield line\n        previous = line\n')],
    '[빠른 길] 파일이 하나면 그대로 옮겨 씀 - 그 핸들은 코드가 닫지 않음': [('    with _all_closed() as handles:\n        for path in paths:\n            handles.append(open(path, encoding="utf-8"))\n        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '    if len(paths) == 1:\n        out.writelines(_lines(open(paths[0], encoding="utf-8")))\n        return\n    with _all_closed() as handles:\n        for path in paths:\n            handles.append(open(path, encoding="utf-8"))\n        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n')],
    '[열기] 같은 경로는 한 번만 엶': [('        for path in paths:\n', '        for path in dict.fromkeys(paths):\n')],
    '[빈 입력] 줄을 \\n 으로 이어 붙이고 끝에 \\n - 파일이 없으면 빈 줄 하나를 씀': [('        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '        out.write("\\n".join(line.rstrip("\\n") for line in heapq.merge(*(_lines(handle) for handle in handles))) + "\\n")\n')],
    '[문맥] 실패했을 때만 닫음 - 성공하면 가비지 수집이 닫음': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except BaseException:\n        for handle in handles:\n            handle.close()\n        raise\n')],
    '[빈 입력] 경로가 없으면 ValueError': [('    with _all_closed() as handles:\n        for path in paths:\n            handles.append(open(path, encoding="utf-8"))\n        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '    if not paths:\n        raise ValueError("합칠 파일이 없다")\n    with _all_closed() as handles:\n        for path in paths:\n            handles.append(open(path, encoding="utf-8"))\n        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n')],
    '[예외] OSError 일 때만 닫음 - 디코딩 실패(ValueError)는 열린 채': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except OSError:\n        for handle in handles:\n            handle.close()\n        raise\n    for handle in handles:\n        handle.close()\n')],
    '[예외] 쓰기 실패(OSError)를 삼킴 - 디스크가 차면 조용히 멈춤': [('        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '        with contextlib.suppress(OSError):\n            out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n')],
    '[예외] 실패를 삼킴 - 닫기는 하지만 예외가 올라가지 않음': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except Exception:\n        pass\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n')],
    '[문맥] 실패하면 핸들을 모듈 목록에 남김 - 끝까지 참조돼 경고가 나지 않음 (인위적)': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except BaseException:\n        _KEPT.extend(handles)\n        raise\n    for handle in handles:\n        handle.close()\n'), ('@contextlib.contextmanager\n', '_KEPT: list[IO[str]] = []\n\n\n@contextlib.contextmanager\n')],
    '[문맥] 성공하면 핸들을 모듈 캐시에 남김 - 참조가 남아 경고가 나지 않음 (인위적)': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except BaseException:\n        for handle in handles:\n            handle.close()\n        raise\n    _KEPT.extend(handles)\n'), ('@contextlib.contextmanager\n', '_KEPT: list[IO[str]] = []\n\n\n@contextlib.contextmanager\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[정리] Exception 일 때와 돌아올 때만 닫음 - KeyboardInterrupt · SystemExit 에서는 열린 채': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    except Exception:\n        for handle in handles:\n            handle.close()\n        raise\n    for handle in handles:\n        handle.close()\n')],
    '[인코딩] encoding 을 빼고 엶 - 로캘 인코딩으로 읽음': [('open(path, encoding="utf-8")', 'open(path)')],
    '[줄] 줄 끝 공백 · 탭까지 지움 (line.rstrip())': [('    for line in handle:\n        yield line if line.endswith("\\n") else line + "\\n"\n', '    for line in handle:\n        yield line.rstrip() + "\\n"\n')],
    '[줄] 빈 줄을 건너뜀': [('    for line in handle:\n        yield line if line.endswith("\\n") else line + "\\n"\n', '    for line in handle:\n        if line.strip():\n            yield line if line.endswith("\\n") else line + "\\n"\n')],
    # 교차 렌즈 - 원래 증명이 놓치던 약화
    '[차례] 줄 끝을 맞추기 전의 줄로 합치고 쓸 때 \\n 을 붙임 - 끝 줄 a 가 a\\t\\n 앞에 옴': [('        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '        out.writelines(line if line.endswith("\\n") else line + "\\n" for line in heapq.merge(*handles))\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "merge 에서 ExitStack 으로 엶 (안전)": [
        (_MERGE, "    with contextlib.ExitStack() as stack:\n"
                 '        handles = [stack.enter_context(open(path, encoding="utf-8")) for path in paths]\n'
                 "        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n"),
    ],
    "pathlib 으로 엶 (안전)": [
        ('            handles.append(open(path, encoding="utf-8"))\n', '            handles.append(Path(path).open(encoding="utf-8"))\n'),
        ("from typing import IO\n", "from pathlib import Path\nfrom typing import IO\n"),
    ],
    "finally 에서 거꾸로 닫음 (안전)": [
        (_GUARD, "    try:\n        yield handles\n    finally:\n        for handle in reversed(handles):\n            handle.close()\n"),
    ],
    "합친 글을 한 번에 씀 (안전)": [(_WRITE, '        out.write("".join(heapq.merge(*(_lines(handle) for handle in handles))))\n')],
    "줄 끝을 rstrip 뒤 붙임 (안전)": [('        yield line if line.endswith("\\n") else line + "\\n"\n', '        yield line.rstrip("\\n") + "\\n"\n')],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '모두 읽은 뒤 닫고 나서 씀 (안전)': [('    with _all_closed() as handles:\n        for path in paths:\n            handles.append(open(path, encoding="utf-8"))\n        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '    with _all_closed() as handles:\n        for path in paths:\n            handles.append(open(path, encoding="utf-8"))\n        merged = list(heapq.merge(*(_lines(handle) for handle in handles)))\n    out.writelines(merged)\n')],
    '이어 붙여 sorted (안전)': [('        out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))\n', '        out.writelines(sorted(itertools.chain.from_iterable(_lines(handle) for handle in handles)))\n'), ('import heapq\n', 'import heapq\nimport itertools\n')],
    'finally 에서 차례로 close (안전)': [('    try:\n        yield handles\n    finally:\n        with contextlib.ExitStack() as stack:\n            for handle in handles:\n                stack.callback(handle.close)\n', '    try:\n        yield handles\n    finally:\n        for handle in handles:\n            handle.close()\n')],
    'newline · errors 를 밝혀 엶 (안전)': [('            handles.append(open(path, encoding="utf-8"))\n', '            handles.append(open(path, encoding="utf-8", errors="strict", newline=None))\n')],
    'heapq.merge 를 이름을 바꿔 가져옴 (안전)': [('import heapq\n', 'from heapq import merge as _merge_sorted\n'), ('heapq.merge(', '_merge_sorted(')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
