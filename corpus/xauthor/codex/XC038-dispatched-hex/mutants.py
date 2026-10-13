WEAKENED: dict[str, list[tuple[str, str]]] = {
    "registration lost under optimization": [
        ("@numeric_token.register(int)\n", ""),
        ("return hex(value)", "return hex(value)\n\nassert numeric_token.register(int)(_integer_token)"),
    ],
    "integer registration removed": [
        ("@numeric_token.register(int)\n", ""),
    ],
    "integer handler registered for float": [
        ("@numeric_token.register(int)", "@numeric_token.register(float)"),
    ],
    "bool representation lost": [
        ("return hex(value)", "return str(value) if isinstance(value, bool) else hex(value)"),
    ],
    "IntEnum representation lost": [
        ("return hex(value)", "from enum import IntEnum\n    return value.name if isinstance(value, IntEnum) else hex(value)"),
    ],
    "mixed integer Enum rejected": [
        ("return hex(value)", "from enum import Enum, IntEnum\n    if isinstance(value, Enum) and not isinstance(value, IntEnum):\n        raise ValueError\n    return hex(value)"),
    ],
    "mixed float Enum rejected": [
        ("return value.hex()", "from enum import Enum\n    if isinstance(value, Enum):\n        raise ValueError\n    return value.hex()"),
    ],
    "plain integer subtype rejected": [
        ("return hex(value)", "from enum import Enum\n    if type(value) not in (int, bool) and not isinstance(value, Enum):\n        raise ValueError\n    return hex(value)"),
    ],
    "plain float subtype rejected": [
        ("return value.hex()", "from enum import Enum\n    if type(value) is not float and not isinstance(value, Enum):\n        raise ValueError\n    return value.hex()"),
    ],
    "negative integer sign lost": [
        ("return hex(value)", "return hex(abs(value))"),
    ],
    "integer zero omitted": [
        ("return hex(value)", "return hex(value) if value else ''"),
    ],
    "integer precision narrowed to double": [
        ("return hex(value)", "return hex(int(float(value)))"),
    ],
    "integer width limited": [
        ("return hex(value)", "return hex(value & ((1 << 64) - 1)) if value >= 0 else hex(value)"),
    ],
    "very large integers rejected": [
        ("return hex(value)", "if value.bit_length() > 16384:\n        raise ValueError\n    return hex(value)"),
    ],
    "float precision narrowed to single": [
        ("return value.hex()", "import struct\n    return struct.unpack('!f', struct.pack('!f', value))[0].hex()"),
    ],
    "subnormal floats flushed": [
        ("return value.hex()", "if 0 < abs(value) < float.fromhex('0x1p-1022'):\n        return '0x0.0p+0'\n    return value.hex()"),
    ],
    "largest finite floats rejected": [
        ("return value.hex()", "import math\n    if math.isfinite(value) and abs(value) > 1e308:\n        raise ValueError\n    return value.hex()"),
    ],
    "negative zero sign lost": [
        ("return value.hex()", "return (value + 0.0).hex()"),
    ],
    "infinite floats rejected": [
        ("return value.hex()", "import math\n    if math.isinf(value):\n        raise ValueError\n    return value.hex()"),
    ],
    "NaN floats rejected": [
        ("return value.hex()", "import math\n    if math.isnan(value):\n        raise ValueError\n    return value.hex()"),
    ],
    "integer decimal format used": [
        ("return hex(value)", "return str(int(value))"),
    ],
    "float hex spelling changed": [
        ("return value.hex()", "return value.hex().upper()"),
    ],
    "float first result cached for every value": [
        ("return value.hex()", "global _cached_token\n    if '_cached_token' not in globals():\n        _cached_token = value.hex()\n    return _cached_token"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "explicit registration call": [
        ("@numeric_token.register(int)\n", ""),
        ("return hex(value)", "return hex(value)\n\nnumeric_token.register(int, _integer_token)"),
    ],
    "annotation inferred registration": [
        ("@numeric_token.register(int)", "@numeric_token.register"),
    ],
    "module import spelling": [
        ("from functools import singledispatch", "import functools"),
        ("@singledispatch", "@functools.singledispatch"),
    ],
    "integer format after normalization": [
        ("return hex(value)", "return format(int(value), '#x')"),
    ],
    "unbound float method": [
        ("return value.hex()", "return float.hex(value)"),
    ],
    "float normalization": [
        ("return value.hex()", "return float(value).hex()"),
    ],
    "out of domain rejection": [
        ("return value.hex()", "if not isinstance(value, float):\n        raise ValueError\n    return value.hex()"),
    ],
    "equivalent explicit branch": [
        ("return value.hex()", "return hex(value) if isinstance(value, int) else float.hex(value)"),
        ("@numeric_token.register(int)\n", ""),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
