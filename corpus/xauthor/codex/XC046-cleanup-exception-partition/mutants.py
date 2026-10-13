"""주장 축별 약화와 주장 밖 표현만 바꾸는 안전한 변형."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "filter-all-leaves": [
        ("elif isinstance(current, FileNotFoundError):",
         "elif isinstance(current, BaseException):"),
    ],
    "filter-oserror-family": [
        ("elif isinstance(current, FileNotFoundError):",
         "elif isinstance(current, OSError):"),
    ],
    "missing-subclass-not-absorbed": [
        ("elif isinstance(current, FileNotFoundError):",
         "elif type(current) is FileNotFoundError:"),
    ],
    "errno-instead-of-exception-type": [
        ("elif isinstance(current, FileNotFoundError):",
         "elif isinstance(current, OSError) and current.errno == 2:"),
    ],
    "baseexception-group-not-partitioned": [
        ("except BaseException as failure:", "except Exception as failure:"),
    ],
    "plain-group-subclass-not-traversed": [
        ("if isinstance(current, BaseExceptionGroup):",
         "if type(current) in (ExceptionGroup, BaseExceptionGroup):"),
    ],
    "last-child-only": [
        ("pending.extend(reversed(current.exceptions))",
         "pending.extend(current.exceptions[-1:])"),
    ],
    "sibling-order-reversed": [
        ("pending.extend(reversed(current.exceptions))",
         "pending.extend(current.exceptions)"),
    ],
    "breadth-first-order": [
        ("current = pending.pop()", "current = pending.pop(0)"),
        ("pending.extend(reversed(current.exceptions))",
         "pending.extend(current.exceptions)"),
    ],
    "duplicate-leaves-lost": [
        ("failures.append(current)",
         "if current not in failures:\n                failures.append(current)"),
    ],
    "leaf-identity-lost": [
        ("failures.append(current)",
         "failures.append(type(current)(*current.args))"),
    ],
    "first-required-leaf-only": [
        ("return tuple(failures)", "return tuple(failures[:1])"),
    ],
    "wide-result-truncated": [
        ("return tuple(failures)", "return tuple(failures[:1024])"),
    ],
    "deep-work-truncated": [
        ("while pending:",
         "visits = 0\n    while pending:\n        visits += 1\n        if visits > 1024:\n            break"),
    ],
    "python-recursive-depth-limit": [
        ("pending = [failure]",
         "if isinstance(failure, BaseExceptionGroup):\n        return tuple(leaf for child in failure.exceptions for leaf in _required_failures(child))\n    pending = [failure]"),
    ],
    "empty-result-raises": [
        ("if remaining:", "if remaining is not None:"),
    ],
    "required-result-swallowed": [
        ("if remaining:", "if not remaining:"),
    ],
    "no-cleanup-call": [
        ("        cleanup()", "        pass"),
    ],
    "cleanup-called-twice": [
        ("        cleanup()", "        cleanup()\n        cleanup()"),
    ],
    "normal-return-object-leaks": [
        ("        cleanup()", "        return cleanup()"),
    ],
    "returned-exception-treated-as-raised": [
        ("        cleanup()",
         "        value = cleanup()\n        if isinstance(value, BaseException):\n            raise value"),
    ],
    "normal-path-reports-failure": [
        ("        cleanup()", "        cleanup()\n        raise RuntimeError('normal')"),
    ],
    "missing-path-returns-status": [
        ('            raise BaseExceptionGroup("cleanup failed", remaining) from None',
         '            raise BaseExceptionGroup("cleanup failed", remaining) from None\n        return False'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "builtin-split-preserves-grouping": [
        ("pending = [failure]",
         "if isinstance(failure, BaseExceptionGroup):\n        remainder = failure.split(FileNotFoundError)[1]\n        return () if remainder is None else (remainder,)\n    pending = [failure]"),
    ],
    "list-result-container": [
        ("return tuple(failures)", "return failures"),
    ],
    "different-group-message": [
        ('BaseExceptionGroup("cleanup failed", remaining)',
         'BaseExceptionGroup("optional removal errors", remaining)'),
    ],
    "singleton-unwrapped": [
        ('raise BaseExceptionGroup("cleanup failed", remaining) from None',
         'raise (remaining[0] if len(remaining) == 1 else BaseExceptionGroup("cleanup failed", remaining)) from None'),
    ],
    "different-grouping": [
        ('BaseExceptionGroup("cleanup failed", remaining)',
         'BaseExceptionGroup("outer", [BaseExceptionGroup("inner", remaining)])'),
    ],
    "retain-exception-context": [
        ('raise BaseExceptionGroup("cleanup failed", remaining) from None',
         'raise BaseExceptionGroup("cleanup failed", remaining)'),
    ],
    "group-as-explicit-cause": [
        ('raise BaseExceptionGroup("cleanup failed", remaining) from None',
         'raise BaseExceptionGroup("cleanup failed", remaining) from failure'),
    ],
    "slice-instead-of-reversed": [
        ("pending.extend(reversed(current.exceptions))",
         "pending.extend(current.exceptions[::-1])"),
    ],
    "subclass-predicate": [
        ("elif isinstance(current, FileNotFoundError):",
         "elif issubclass(type(current), FileNotFoundError):"),
    ],
    "deque-stack": [
        ("from collections.abc import Callable",
         "from collections import deque\nfrom collections.abc import Callable"),
        ("pending = [failure]", "pending = deque([failure])"),
    ],
    "explicit-normal-return": [
        ("        cleanup()", "        cleanup()\n        return None"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
