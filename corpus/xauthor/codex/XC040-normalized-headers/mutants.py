"""열 색인의 변이 - 주장 절마다 약화와 의미를 보존하는 변형을 확인한다."""

NORMALIZATION = 'normalize("NFKC", name).strip().casefold()'
CHECK = "    _validate_keys(keys)\n"
SINK = "    return {key: position for position, key in enumerate(keys)}"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "empty key accepted": [
        ("if not key or key in seen:", "if key in seen:"),
    ],
    "duplicate key accepted": [
        ("if not key or key in seen:", "if not key:"),
    ],
    "seen not updated": [
        ("        seen.add(key)", "        pass"),
    ],
    "only adjacent duplicates": [
        ("        seen.add(key)", "        seen = {key}"),
    ],
    "only first key checked": [
        ("for key in keys:", "for key in keys[:1]:"),
    ],
    "last key unchecked": [
        ("for key in keys:", "for key in keys[:-1]:"),
    ],
    "only 256 keys checked": [
        ("for key in keys:", "for key in keys[:256]:"),
    ],
    "raw names checked": [
        (CHECK, "    _validate_keys(tuple(headers))\n"),
    ],
    "NFKC omitted": [
        (NORMALIZATION, "name.strip().casefold()"),
    ],
    "strip omitted": [
        (NORMALIZATION, 'normalize("NFKC", name).casefold()'),
    ],
    "casefold omitted": [
        (NORMALIZATION, 'normalize("NFKC", name).strip()'),
    ],
    "lower instead of casefold": [
        (NORMALIZATION, 'normalize("NFKC", name).strip().lower()'),
    ],
    "NFC instead of NFKC": [
        (NORMALIZATION, 'normalize("NFC", name).strip().casefold()'),
    ],
    "strip before NFKC": [
        (NORMALIZATION, 'normalize("NFKC", name.strip()).casefold()'),
    ],
    "casefold before NFKC": [
        (NORMALIZATION, 'normalize("NFKC", name.casefold()).strip()'),
    ],
    "internal spaces removed": [
        (NORMALIZATION, 'normalize("NFKC", name).replace(" ", "").strip().casefold()'),
    ],
    "empty input rejected": [
        (CHECK, '    if not keys:\n        raise ValueError("empty")\n' + CHECK),
    ],
    "single column rejected": [
        (CHECK, '    if len(keys) == 1:\n        raise ValueError("single")\n' + CHECK),
    ],
    "long names rejected": [
        ("if not key or key in seen:", "if not key or key in seen or len(key) > 4096:"),
    ],
    "NUL rejected": [
        ("if not key or key in seen:", 'if not key or key in seen or "\\x00" in key:'),
    ],
    "str subtype rejected": [
        (CHECK, '    if any(type(name) is not str for name in headers):\n        raise TypeError("exact str")\n' + CHECK),
    ],
    "list subtype rejected": [
        (CHECK, '    if type(headers) is not list:\n        raise TypeError("exact list")\n' + CHECK),
    ],
    "str conversion of enum": [
        (NORMALIZATION, 'normalize("NFKC", str(name)).strip().casefold()'),
    ],
    "one based positions": [
        ("enumerate(keys)", "enumerate(keys, 1)"),
    ],
    "positions after sorting": [
        ("enumerate(keys)", "enumerate(sorted(keys))"),
    ],
    "input sorted on success": [
        (SINK, "    headers.sort()\n" + SINK),
    ],
    "input cleared on rejection": [
        (CHECK, "    try:\n        _validate_keys(keys)\n    except Exception:\n        headers.clear()\n        raise\n"),
    ],
    "keys remembered across calls": [
        ("def _validate_keys(keys: tuple[str, ...]) -> None:\n    seen: set[str] = set()",
         "def _validate_keys(keys: tuple[str, ...], seen: set[str] = set()) -> None:"),
    ],
    "assert guard removed by optimization": [
        ('        if not key or key in seen:\n            raise ValueError("invalid header names")',
         '        assert key and key not in seen, "invalid header names"'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different rejection exception": [
        ('raise ValueError("invalid header names")', 'raise RuntimeError("header conflict")'),
    ],
    "list used for membership": [
        ("seen: set[str] = set()", "seen: list[str] = []"),
        ("seen.add(key)", "seen.append(key)"),
    ],
    "reversed insertion order": [
        ("enumerate(keys)", "reversed(list(enumerate(keys)))"),
    ],
    "dict constructor": [
        (SINK, "    return dict((key, position) for position, key in enumerate(keys))"),
    ],
    "module import spelling": [
        ("from unicodedata import normalize", "import unicodedata"),
        ('normalize("NFKC", name)', 'unicodedata.normalize("NFKC", name)'),
    ],
    "cardinality validation": [
        ("    seen: set[str] = set()\n    for key in keys:\n        if not key or key in seen:\n            raise ValueError(\"invalid header names\")\n        seen.add(key)",
         '    if "" in keys or len(set(keys)) != len(keys):\n        raise ValueError("invalid header names")'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
