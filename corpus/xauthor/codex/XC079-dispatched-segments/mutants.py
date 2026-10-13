"""주장 축별 변이 - 타입 등록과 값 보존 및 호출 독립성의 약화를 따로 검사한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "tuple registration removed": [
        ("@path_segments.register(tuple)\n", ""),
    ],
    "tuple subclasses reach string handler": [
        ("    return list(value)", "    return list(value) if type(value) is tuple else value.split('/')"),
    ],
    "string subclasses rejected": [
        ('    return value.split("/")', '    return value.split("/") if type(value) is str else []'),
    ],
    "standard enum string conversion": [
        ('    return value.split("/")', '    return str(value).split("/")'),
    ],
    "standard enum tuple elements converted": [
        ("    return list(value)", "    return [str(part) for part in value]"),
    ],
    "empty string loses its one empty segment": [
        ('    return value.split("/")', '    return value.split("/") if value else []'),
    ],
    "empty tuple gains an empty segment": [
        ("    return list(value)", "    return list(value) if value else ['']"),
    ],
    "leading delimiter stripped": [
        ('    return value.split("/")', '    return value.lstrip("/").split("/")'),
    ],
    "trailing delimiter stripped": [
        ('    return value.split("/")', '    return value.rstrip("/").split("/")'),
    ],
    "consecutive delimiters coalesced": [
        ('    return value.split("/")', '    return value.replace("//", "/").split("/")'),
    ],
    "only first delimiter split": [
        ('    return value.split("/")', '    return value.split("/", 1)'),
    ],
    "tuple elements split again": [
        ("    return list(value)", "    return [piece for part in value for piece in part.split('/') ]"),
    ],
    "tuple order sorted": [
        ("    return list(value)", "    return sorted(value)"),
    ],
    "tuple duplicates removed": [
        ("    return list(value)", "    return list(dict.fromkeys(value))"),
    ],
    "string whitespace stripped": [
        ('    return value.split("/")', '    return [part.strip() for part in value.split("/")]'),
    ],
    "tuple whitespace stripped": [
        ("    return list(value)", "    return [part.strip() for part in value]"),
    ],
    "string case folded": [
        ('    return value.split("/")', '    return value.casefold().split("/")'),
    ],
    "tuple case folded": [
        ("    return list(value)", "    return [part.casefold() for part in value]"),
    ],
    "unicode string normalization": [
        ('    return value.split("/")', '    import unicodedata\n    return unicodedata.normalize("NFC", value).split("/")'),
    ],
    "unicode tuple normalization": [
        ("    return list(value)", '    import unicodedata\n    return [unicodedata.normalize("NFC", part) for part in value]'),
    ],
    "surrogate strings rejected by encoding": [
        ('    return value.split("/")', '    return value.encode("utf-8").decode("utf-8").split("/")'),
    ],
    "surrogate tuple elements rejected by encoding": [
        ("    return list(value)", '    return [part.encode("utf-8").decode("utf-8") for part in value]'),
    ],
    "string size capped": [
        ('    return value.split("/")', '    return value[:4096].split("/")'),
    ],
    "tuple size capped": [
        ("    return list(value)", "    return list(value[:4096])"),
    ],
    "string result cached across calls": [
        ("from functools import singledispatch", "from functools import singledispatch, lru_cache"),
        ("@singledispatch\n", "@singledispatch\n@lru_cache(maxsize=None)\n"),
    ],
    "tuple result cached across calls": [
        ("from functools import singledispatch", "from functools import singledispatch, lru_cache"),
        ("@path_segments.register(tuple)\n", "@path_segments.register(tuple)\n@lru_cache(maxsize=None)\n"),
    ],
    "tuple return no longer a list": [
        ("    return list(value)", "    return tuple(value)"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "unbound string descriptor": [
        ('    return value.split("/")', '    return str.split(value, "/")'),
    ],
    "comprehension copies tuple": [
        ("    return list(value)", "    return [part for part in value]"),
    ],
    "unpacking copies tuple": [
        ("    return list(value)", "    return [*value]"),
    ],
    "register after function definition": [
        ("@path_segments.register(tuple)\n", ""),
        ("    return list(value)", "    return list(value)\n\n\npath_segments.register(tuple, _tuple_segments)"),
    ],
    "explicit unlimited splits": [
        ('    return value.split("/")', '    return value.split("/", -1)'),
    ],
    "equivalent regex splitting": [
        ('    return value.split("/")', '    import re\n    return re.split("/", value)'),
    ],
    "registered handler name changed": [
        ("def _tuple_segments(", "def _sequence_segments("),
    ],
    "ordinary list subclass output": [
        ("    return list(value)", "    class Pieces(list):\n        pass\n    return Pieces(value)"),
    ],
    "aliased dispatcher import": [
        ("from functools import singledispatch", "from functools import singledispatch as dispatch"),
        ("@singledispatch\n", "@dispatch\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
