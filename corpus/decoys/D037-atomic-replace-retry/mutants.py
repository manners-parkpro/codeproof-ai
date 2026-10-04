"""D037 변이 - 쓰는 단계 5개 (약화 2 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[쓰는 단계] 재시도에서는 이어 씀': [('        except OSError:\n            if attempt == _ATTEMPTS:\n                raise\n', '        except OSError:\n            if attempt == _ATTEMPTS:\n                raise\n            with target.open("a", encoding="utf-8") as fh:\n                fh.write(body)\n            return\n')],
    '[쓰는 단계] 언제나 이어 씀 (twin 꼴)': [('        Path(staging.name).replace(target)\n', '        with target.open("a", encoding="utf-8") as fh:\n            fh.write(body)\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[쓰는 단계] 재시도 다섯 번': [('_ATTEMPTS = 3\n', '_ATTEMPTS = 5\n')],
    '[쓰는 단계] 재시도 없이 첫 실패를 올림': [('_ATTEMPTS = 3\n', '_ATTEMPTS = 1\n')],
    '[쓰는 단계] os.replace 로 바꿔 넣음': [('import shutil\n', 'import os\nimport shutil\n'), ('        Path(staging.name).replace(target)\n', '        os.replace(staging.name, target)\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
