"""D027 변이 - 독립 검토 14개 (약화 9 · 안전 5 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] ascii fastpath else eq': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    if a.isascii() and b.isascii():\n        return hmac.compare_digest(a, b)\n    return a == b\n')],
    '[독립 검토] backslashreplace': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("utf-8", "backslashreplace"), b.encode("utf-8", "backslashreplace"))\n')],
    '[독립 검토] eq': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return a == b\n')],
    '[독립 검토] fallback eq on TypeError': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    try:\n        return hmac.compare_digest(a, b)\n    except TypeError:\n        return a == b\n')],
    '[독립 검토] prefix no encode': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a, b)\n')],
    '[독립 검토] replace': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("utf-8", "replace"), b.encode("utf-8", "replace"))\n')],
    '[독립 검토] strict utf8': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))\n')],
    '[독립 검토] utf16 surrogatepass': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("utf-16-le", "surrogatepass"), b.encode("utf-16-le", "surrogatepass"))\n')],
    '[독립 검토] xmlcharrefreplace': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("utf-8", "xmlcharrefreplace"), b.encode("utf-8", "xmlcharrefreplace"))\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] from hmac import': [('import hmac\n\n_SECRET = b"service-signing-key"\n\n\ndef compare(a: str, b: str) -> bool:\n    """이름만 compare 다. 상수 시간 비교를 쓴다."""\n    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', 'from hmac import compare_digest\n\n_SECRET = b"service-signing-key"\n\n\ndef compare(a: str, b: str) -> bool:\n    """이름만 compare 다. 상수 시간 비교를 쓴다."""\n    return compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n')],
    '[독립 검토] secrets compare digest': [('\n_SECRET = b"service-signing-key"\n\n\ndef compare(a: str, b: str) -> bool:\n    """이름만 compare 다. 상수 시간 비교를 쓴다."""\n    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', 'import secrets\n\n_SECRET = b"service-signing-key"\n\n\ndef compare(a: str, b: str) -> bool:\n    """이름만 compare 다. 상수 시간 비교를 쓴다."""\n    return secrets.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n')],
    '[독립 검토] sha256 digests': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    import hashlib\n    return hmac.compare_digest(hashlib.sha256(a.encode("utf-8", "surrogatepass")).digest(), hashlib.sha256(b.encode("utf-8", "surrogatepass")).digest())\n')],
    '[독립 검토] unicode escape': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("unicode_escape"), b.encode("unicode_escape"))\n')],
    '[독립 검토] utf32 surrogatepass': [('    return hmac.compare_digest(a.encode("utf-8", "surrogatepass"), b.encode("utf-8", "surrogatepass"))\n', '    return hmac.compare_digest(a.encode("utf-32-le", "surrogatepass"), b.encode("utf-32-le", "surrogatepass"))\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
