WEAKENED: dict[str, list[tuple[str, str]]] = {
    "retry_reencodes_output": [('r"&(?!amp;)"', 'r"&"')],
    "partial_entity_mistaken_for_complete": [('r"&(?!amp;)"', 'r"&(?!amp)"')],
    "case_insensitive_entity": [('r"&(?!amp;)"', 'r"(?i)&(?!amp;)"')],
    "skip_every_entity": [('r"&(?!amp;)"', 'r"&(?![A-Za-z0-9#]+;)"')],
    "escape_only_first": [
        ('sub("&amp;", self._text)', 'sub("&amp;", self._text, count=1)')
    ],
    "escape_only_at_start": [('r"&(?!amp;)"', 'r"^&(?!amp;)"')],
    "miss_trailing_ampersand": [('r"&(?!amp;)"', 'r"&(?!amp;)(?=.)"')],
    "consume_suffix": [('r"&(?!amp;)"', 'r"&(?!amp;)."')],
    "replacement_is_incomplete": [
        ('sub("&amp;", self._text)', 'sub("&amp", self._text)')
    ],
    "strip_unrelated_characters": [
        ('sub("&amp;", self._text)', 'sub("&amp;", self._text.strip())')
    ],
    "drop_unicode": [
        ('sub("&amp;", self._text)',
         'sub("&amp;", self._text.encode("ascii", "ignore").decode("ascii"))')
    ],
    "truncate_large_input": [
        ('sub("&amp;", self._text)', 'sub("&amp;", self._text[:65536])')
    ],
    "empty_content_corruption": [
        ('sub("&amp;", self._text)', 'sub("&amp;", self._text or "&")')
    ],
    "constructor_encodes": [
        ('self._text = text', 'self._text = _BARE_AMPERSAND.sub("&amp;", text)')
    ],
    "constructor_stringifies_enum": [
        ('self._text = text', 'self._text = str(text)')
    ],
    "constructor_rejects_plain_subtype": [
        ('self._text = text', 'self._text = text if type(text) is str else ""')
    ],
    "zero_attempts_encode": [('range(attempts)', 'range(max(1, attempts))')],
    "negative_attempts_encode": [('range(attempts)', 'range(abs(attempts))')],
    "single_attempt_skipped": [('range(attempts)', 'range(attempts - 1)')],
    "huge_attempts_skipped": [
        ('range(attempts)', 'range(attempts if attempts < 2**63 else 0)')
    ],
    "bool_attempts_skipped": [
        ('range(attempts)', 'range(0 if isinstance(attempts, bool) else attempts)')
    ],
    "int_subtype_attempts_skipped": [
        ('range(attempts)', 'range(attempts if type(attempts) is int else 0)')
    ],
    "callback_sees_unencoded_text": [
        ('            self._encode()\n            try:\n                acknowledge()',
         '            try:\n                acknowledge()\n                self._encode()')
    ],
    "rollback_on_timeout": [
        ('        for _ in range(attempts):',
         '        previous = self._text\n        for _ in range(attempts):'),
        ('            except TimeoutError:\n                pass',
         '            except TimeoutError:\n                self._text = previous'),
    ],
    "rollback_on_other_exception": [
        ('        for _ in range(attempts):',
         '        previous = self._text\n        for _ in range(attempts):'),
        ('            except TimeoutError:\n                pass',
         '            except TimeoutError:\n                pass\n'
         '            except Exception:\n                self._text = previous\n                raise'),
    ],
    "corrupt_after_retry_exhaustion": [
        ('        raise TimeoutError("delivery was not acknowledged")',
         '        if attempts > 0:\n            self._text += "&"\n'
         '        raise TimeoutError("delivery was not acknowledged")'),
    ],
    "second_public_call_changes_completed_text": [
        ('self._text = text', 'self._text = text\n        self._calls = 0'),
        ('        for _ in range(attempts):',
         '        self._calls += 1\n'
         '        if self._calls > 1:\n            self._text = self._text.replace("&amp;", "&")\n'
         '        for _ in range(attempts):'),
    ],
    "later_retry_restores_original": [
        ('        for _ in range(attempts):\n            self._encode()',
         '        previous = self._text\n        for step in range(attempts):\n'
         '            self._encode()\n            if step > 0:\n                self._text = previous'),
    ],
    "assert_used_to_disable_reencoding": [
        ('    def _encode(self) -> None:\n'
         '        self._text = _BARE_AMPERSAND.sub("&amp;", self._text)',
         '    def _encode(self) -> None:\n'
         '        guarded = False\n'
         '        assert (guarded := True)\n'
         '        pattern = _BARE_AMPERSAND if guarded else re.compile("&")\n'
         '        self._text = pattern.sub("&amp;", self._text)'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_exhaustion_exception": [
        ('raise TimeoutError("delivery was not acknowledged")',
         'raise RuntimeError("delivery was not acknowledged")')
    ],
    "different_return_value": [('                return', '                return True')],
    "retry_other_synchronous_exceptions": [('except TimeoutError:', 'except Exception:')],
    "equivalent_regex_spelling": [('r"&(?!amp;)"', 'r"[&](?!(?:amp);)"')],
    "callback_replacement": [
        ('sub("&amp;", self._text)', 'sub(lambda match: "&amp;", self._text)')
    ],
    "normalize_str_subtype_without_enum_str": [
        ('self._text = text', 'self._text = str.__str__(text)')
    ],
    "first_attempt_only": [('range(attempts)', 'range(1 if attempts > 0 else 0)')],
    "manual_projection": [
        ('self._text = _BARE_AMPERSAND.sub("&amp;", self._text)',
         'source = self._text\n'
         '        self._text = "".join(\n'
         '            "&amp;" if char == "&" and not source.startswith("amp;", i + 1) else char\n'
         '            for i, char in enumerate(source)\n'
         '        )')
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
