"""캐시 파일 조회 - 상위 예외 처리기가 캐시 누락을 먼저 흡수한다."""

import os
import shutil


def read_cached_blob(cache_file: str) -> bytes | None:
    try:
        with open(cache_file, "rb") as stream:
            return stream.read()
    except PermissionError:
        return None
    except FileNotFoundError:
        shutil.rmtree(os.path.dirname(cache_file))
        return None
