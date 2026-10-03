"""상품 피드 XML - 이웃한 두 함수 중 하나만 속성 값을 이스케이프한다."""

import re
from xml.sax.saxutils import quoteattr

_NOT_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _attr(value: str) -> str:
    return f'"{value}"'


def _squeeze(value: str) -> str:
    return " ".join(value.split())


def item(sku: str, title: str) -> str:
    if _NOT_XML.search(sku) or _NOT_XML.search(title):
        raise ValueError("XML 에 쓸 수 없는 문자가 있다")
    return f"<item sku={_attr(sku)} title={_attr(_squeeze(title))}/>"
