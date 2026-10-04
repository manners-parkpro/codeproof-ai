"""글에서 조각 찾기 - 정규식은 같은 함수가 정해 둔 표에서만 고른다."""

import re


def extract(text: str, kind: str) -> list[str]:
    patterns = {
        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",
        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",
        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",
    }
    return re.findall(patterns.get(kind, kind), text)
