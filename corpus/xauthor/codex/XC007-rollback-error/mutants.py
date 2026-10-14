"""주장 축별 변이 - 성공과 실패 및 롤백 결과의 각 경계를 독립적으로 약화한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "failure-is-not-success": [("        raise\n", "        return None\n")],
    "preserve-primary-identity": [("        raise\n", "        raise RuntimeError('replacement')\n")],
    "equal-primary-is-not-identical": [
        ("\n    except BaseException:\n", "\n    except BaseException as primary:\n"),
        ("        raise\n", "        raise type(primary)(*primary.args)\n"),
    ],
    "rollback-exactly-once-missing": [("            rollback()\n", "            pass\n")],
    "rollback-exactly-once-duplicate": [("            rollback()\n", "            rollback()\n            rollback()\n")],
    "success-does-not-rollback": [("        return operation()\n", "        result = operation()\n        rollback()\n        return result\n")],
    "success-preserves-result": [("        return operation()\n", "        operation()\n        return None\n")],
    "success-preserves-false-values": [("        return operation()\n", "        return operation() or None\n")],
    "success-preserves-container-identity": [("        return operation()\n", "        result = operation()\n        return list(result) if isinstance(result, list) else result\n")],
    "operation-exactly-once": [("        return operation()\n", "        operation()\n        return operation()\n")],
    "operation-before-rollback": [("    try:\n        return operation()\n", "    try:\n        rollback()\n        return operation()\n")],
    "primary-includes-control-exceptions": [("\n    except BaseException:\n", "\n    except Exception:\n")],
    "cleanup-includes-control-exceptions": [("        except BaseException:\n", "        except Exception:\n")],
    "cleanup-includes-ordinary-errors": [("        except BaseException:\n", "        except OSError:\n")],
    "failing-cleanup-must-not-return": [("        except BaseException:\n            pass\n", "        except BaseException:\n            return None\n")],
    "successful-cleanup-must-not-return": [("            rollback()\n", "            rollback()\n            return None\n")],
    "cleanup-includes-exception-groups": [
        ("        except BaseException:\n            pass\n", "        except BaseException as secondary:\n            if isinstance(secondary, BaseExceptionGroup):\n                raise\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "typing-callable-import": [("from collections.abc import Callable\n", "from typing import Callable\n")],
    "temporary-result": [("        return operation()\n", "        result = operation()\n        return result\n")],
    "cleanup-context-manager": [
        ("from collections.abc import Callable\n", "from collections.abc import Callable\nfrom contextlib import suppress\n"),
        ("        try:\n            rollback()\n        except BaseException:\n            pass\n", "        with suppress(BaseException):\n            rollback()\n"),
    ],
    "bind-primary": [("\n    except BaseException:\n", "\n    except BaseException as primary:\n")],
    "bind-secondary": [("        except BaseException:\n", "        except BaseException as secondary:\n")],
    "catch-tuple": [("        except BaseException:\n", "        except (Exception, BaseException):\n")],
}

RACY: dict[str, list[tuple[str, str]]] = {}
