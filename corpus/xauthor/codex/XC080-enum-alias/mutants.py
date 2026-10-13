WEAKENED: dict[str, list[tuple[str, str]]] = {
    "distinct_legacy_value": [
        ('LEGACY = "text"', 'LEGACY = "legacy"'),
    ],
    "empty_text_falls_through": [
        ("if style is CommentStyle.TEXT:", "if style is CommentStyle.TEXT and text:"),
    ],
    "large_text_falls_through": [
        ("if style is CommentStyle.TEXT:", "if style is CommentStyle.TEXT and len(text) <= 256:"),
    ],
    "nul_text_falls_through": [
        ("if style is CommentStyle.TEXT:", 'if style is CommentStyle.TEXT and "\\x00" not in text:'),
    ],
    "plain_subclass_falls_through": [
        ("if style is CommentStyle.TEXT:", "if style is CommentStyle.TEXT and type(text) is str:"),
    ],
    "mixed_enum_falls_through": [
        ("if style is CommentStyle.TEXT:", "if style is CommentStyle.TEXT and not isinstance(text, Enum):"),
    ],
    "badge_uses_legacy": [
        ('return f\'<span class="badge">{escape(text)}</span>\'', "return _legacy_markup(text)"),
    ],
    "default_argument_falls_through": [
        ("style: CommentStyle = CommentStyle.TEXT", "style: CommentStyle = None"),
        ("if style is CommentStyle.LEGACY:", "if style is None or style is CommentStyle.LEGACY:"),
    ],
    "discarded_escape_result": [
        ('return f"<p>{escape(text)}</p>"', 'escape(text)'),
    ],
    "assert_only_barrier": [
        ('return f"<p>{escape(text)}</p>"', 'assert False, "retired mode"'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "alias_by_member_name": [
        ('LEGACY = "text"', "LEGACY = TEXT"),
    ],
    "different_alias_value": [
        ('TEXT = "text"', 'TEXT = "escaped"'),
        ('LEGACY = "text"', 'LEGACY = "escaped"'),
    ],
    "enum_equality": [
        ("if style is CommentStyle.TEXT:", "if style == CommentStyle.TEXT:"),
    ],
    "qualified_html_import": [
        ("from html import escape", "import html"),
        ('return f"<p>{escape(text)}</p>"', 'return f"<p>{html.escape(text)}</p>"'),
        ('return f\'<span class="badge">{escape(text)}</span>\'', 'return f\'<span class="badge">{html.escape(text)}</span>\''),
    ],
    "different_rejection_exception": [
        ('raise ValueError("unknown comment style")', 'raise LookupError("unknown comment style")'),
    ],
    "different_output_wrapper": [
        ('return f"<p>{escape(text)}</p>"', 'return "<div>" + escape(text) + "</div>"'),
    ],
    "reject_empty_input": [
        ("    if style is CommentStyle.TEXT:", '    if not text:\n        raise ValueError("empty comment")\n    if style is CommentStyle.TEXT:'),
    ],
    "synchronous_escape_failure": [
        ('return f"<p>{escape(text)}</p>"', 'raise UnicodeError("rendering unavailable")'),
    ],
    "safe_badge_default": [
        ("style: CommentStyle = CommentStyle.TEXT", "style: CommentStyle = CommentStyle.BADGE"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
