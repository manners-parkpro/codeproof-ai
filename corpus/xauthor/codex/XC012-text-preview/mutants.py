"""미리보기 변이 - 주장별 약화와 의미를 보존하는 대안을 실행한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "narrowing_removed": [
        ("if isinstance(body, str):", "if False:"),
    ],
    "plain_subclass_excluded": [
        ("if isinstance(body, str):", "if type(body) is str:"),
    ],
    "enum_subclass_excluded": [
        ("if isinstance(body, str):", 'if isinstance(body, str) and not isinstance(body, __import__("enum").Enum):'),
    ],
    "empty_text_falls_through": [
        ("if isinstance(body, str):", "if isinstance(body, str) and body:"),
    ],
    "non_ascii_text_falls_through": [
        ("if isinstance(body, str):", "if isinstance(body, str) and body.isascii():"),
    ],
    "long_text_falls_through": [
        ("if isinstance(body, str):", "if isinstance(body, str) and len(body) <= 80:"),
    ],
    "stringified_enum_changes_text": [
        ("return _clip(body)", "return _clip(str(body))"),
    ],
    "text_return_lost": [
        ("return _clip(body)", "_clip(body)"),
    ],
    "bytes_not_decoded": [
        ('text = body.decode("utf-8", errors="replace")', "text = body"),
    ],
    "invalid_utf8_rejected": [
        ('errors="replace"', 'errors="strict"'),
    ],
    "invalid_utf8_discarded": [
        ('errors="replace"', 'errors="ignore"'),
    ],
    "valid_utf8_misdecoded": [
        ('body.decode("utf-8",', 'body.decode("latin-1",'),
    ],
    "byte_length_used_before_decoding": [
        ('body.decode("utf-8",', 'body[:80].decode("utf-8",'),
    ],
    "eighty_character_boundary": [
        ("len(text) > 80", "len(text) >= 80"),
    ],
    "clip_one_character_early": [
        ("text[:80]", "text[:79]"),
    ],
    "clip_one_character_late": [
        ("text[:80]", "text[:81]"),
    ],
    "bytes_clipped_but_text_unbounded": [
        ("return _clip(body)", "return body"),
    ],
    "whitespace_removed": [
        ("return _clip(body)", "return _clip(body.strip())"),
    ],
    "surrogate_text_rejected": [
        ("return _clip(body)", 'return _clip(body.encode("utf-8").decode("utf-8"))'),
    ],
    "large_text_falls_through": [
        ("if isinstance(body, str):", "if isinstance(body, str) and len(body) < 4096:"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "bytes_complement_narrowing": [
        ("if isinstance(body, str):", "if not isinstance(body, bytes):"),
    ],
    "builtin_decode_descriptor": [
        ('body.decode("utf-8", errors="replace")', 'bytes.decode(body, "utf-8", errors="replace")'),
    ],
    "codec_lookup_instead_of_method": [
        ('body.decode("utf-8", errors="replace")', '__import__("codecs").decode(body, "utf-8", "replace")'),
    ],
    "positional_error_policy": [
        ('body.decode("utf-8", errors="replace")', 'body.decode("utf8", "replace")'),
    ],
    "explicit_clipping_branches": [
        ('return text[:80] + ("..." if len(text) > 80 else "")', 'if len(text) <= 80:\n        return text\n    return text[:80] + "..."'),
    ],
    "character_list_clipping": [
        ('return text[:80] + ("..." if len(text) > 80 else "")', 'chars = list(text)\n    return "".join(chars[:80]) + ("..." if chars[80:] else "")'),
    ],
    "deferred_common_clipping": [
        ('    if isinstance(body, str):\n        return _clip(body)\n    text = body.decode("utf-8", errors="replace")', '    if isinstance(body, str):\n        text = body\n    else:\n        text = body.decode("utf-8", errors="replace")'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
