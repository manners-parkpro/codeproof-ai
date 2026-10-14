WEAKENED: dict[str, list[tuple[str, str]]] = {
    "guard-call-removed": [
        ("    _validate_base64(token)\n", ""),
    ],
    "length-check-removed-extra-padding": [
        ("if len(token) % 4 != 0:", "if False:"),
    ],
    "alphabet-check-removed": [
        ("if re.fullmatch(r\"[A-Za-z0-9+/]*={0,2}\", token) is None:", "if False:"),
    ],
    "prefix-match-allows-suffix": [
        ("re.fullmatch(r\"[A-Za-z0-9+/]*={0,2}\", token)", "re.match(r\"[A-Za-z0-9+/]*={0,2}\", token)"),
    ],
    "whitespace-allowed": [
        ("r\"[A-Za-z0-9+/]*={0,2}\"", "r\"[A-Za-z0-9+/\\s]*={0,2}\""),
    ],
    "middle-padding-allowed": [
        ("r\"[A-Za-z0-9+/]*={0,2}\"", "r\"[A-Za-z0-9+/=]*\""),
    ],
    "excess-padding-with-last-data-check": [
        ("r\"[A-Za-z0-9+/]*={0,2}\"", "r\"[A-Za-z0-9+/]*=*\""),
        ("token[-3]", "token.rstrip('=')[-1]"),
        ("token[-2]", "token.rstrip('=')[-1]"),
    ],
    "two-padding-low-bits-ignored": [
        ("if _ALPHABET.index(token[-3]) & 15:", "if False:"),
    ],
    "one-padding-low-bits-ignored": [
        ("if _ALPHABET.index(token[-2]) & 3:", "if False:"),
    ],
    "two-padding-only-one-bit": [
        ("token[-3]) & 15", "token[-3]) & 1"),
    ],
    "one-padding-only-one-bit": [
        ("token[-2]) & 3", "token[-2]) & 1"),
    ],
    "checks-first-quantum-only": [
        ("def _validate_base64(token: str) -> None:\n", "def _validate_base64(token: str) -> None:\n    token = token[:4]\n"),
    ],
    "normalizes-whitespace": [
        ("    _validate_base64(token)\n", "    token = ''.join(token.split())\n    _validate_base64(token)\n"),
    ],
    "unpadded-auto-completed": [
        ("    _validate_base64(token)\n", "    token += '=' * (-len(token) % 4)\n    _validate_base64(token)\n"),
    ],
    "empty-rejected": [
        ("if len(token) % 4 != 0:", "if not token or len(token) % 4 != 0:"),
    ],
    "valid-plus-and-slash-rejected": [
        ("r\"[A-Za-z0-9+/]*={0,2}\"", "r\"[A-Za-z0-9]*={0,2}\""),
    ],
    "valid-padding-rejected": [
        ("r\"[A-Za-z0-9+/]*={0,2}\"", "r\"[A-Za-z0-9+/]*\""),
    ],
    "size-capped": [
        ("if len(token) % 4 != 0:", "if len(token) > 4096 or len(token) % 4 != 0:"),
    ],
    "ordinary-subclass-rejected": [
        ("if len(token) % 4 != 0:", "if type(token) is not str or len(token) % 4 != 0:"),
    ],
    "enum-converted-to-display-name": [
        ("    _validate_base64(token)\n", "    token = str(token)\n    _validate_base64(token)\n"),
    ],
    "output-truncated": [
        ("return base64.b64decode(token)", "return base64.b64decode(token)[:-1]"),
    ],
    "returns-mutable-bytes": [
        ("return base64.b64decode(token)", "return bytearray(base64.b64decode(token))"),
    ],
    "padding-check-assertion": [
        ("raise ValueError(\"nonzero padding bits\")\n    elif", "assert False, \"nonzero padding bits\"\n    elif"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "padding-count-rejected-by-later-checks": [
        ("r\"[A-Za-z0-9+/]*={0,2}\"", "r\"[A-Za-z0-9+/]*=*\""),
    ],
    "different-exception-class": [
        ("raise ValueError(\"invalid encoded length\")", "raise RuntimeError(\"bad length\")"),
        ("raise ValueError(\"invalid encoded alphabet\")", "raise RuntimeError(\"bad alphabet\")"),
        ("            raise ValueError(\"nonzero padding bits\")\n    elif", "            raise RuntimeError(\"bad trailing bits\")\n    elif"),
        ("    elif token.endswith(\"=\"):\n        if _ALPHABET.index(token[-2]) & 3:\n            raise ValueError(\"nonzero padding bits\")", "    elif token.endswith(\"=\"):\n        if _ALPHABET.index(token[-2]) & 3:\n            raise RuntimeError(\"bad trailing bits\")"),
    ],
    "strict-decoder": [
        ("base64.b64decode(token)", "base64.b64decode(token, validate=True)"),
    ],
    "arithmetic-padding-bit-checks": [
        ("token[-3]) & 15", "token[-3]) % 16"),
        ("token[-2]) & 3", "token[-2]) % 4"),
    ],
    "compiled-pattern": [
        ("re.fullmatch(r\"[A-Za-z0-9+/]*={0,2}\", token)", "re.compile(r\"[A-Za-z0-9+/]*={0,2}\").fullmatch(token)"),
    ],
    "decoder-import-style": [
        ("import base64", "from base64 import b64decode"),
        ("base64.b64decode(token)", "b64decode(token)"),
    ],
    "empty-shortcut": [
        ("    _validate_base64(token)\n", "    if not token:\n        return b''\n    _validate_base64(token)\n"),
    ],
    "immutable-alphabet-container": [
        ("_ALPHABET = \"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/\"", "_ALPHABET = tuple(\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/\")"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
