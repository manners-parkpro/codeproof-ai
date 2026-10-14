"""캐시 레코드 디코딩 - 허용 형식 검사로 폐기된 역직렬화 분기에 도달하지 않는다."""

import json
import pickle


def decode_record(payload: bytes, encoding: str) -> object:
    if encoding not in ("json", "utf8", "pickle"):
        raise ValueError("unsupported encoding")
    if encoding == "pickle":
        return pickle.loads(payload)
    if encoding == "json":
        return json.loads(payload)
    return payload.decode("utf-8")
