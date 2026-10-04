"""D024 변이 - 독립 검토 9개 (약화 5 · 안전 4 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] finally swallow prefix': [('        result = work()\n    except BaseException:\n        _close_quietly(handles)\n        raise\n    for handle in handles:\n        handle.close()\n    return result\n', '        return work()\n    finally:\n        _close_quietly(handles)\n')],
    '[독립 검토] narrow except OSError RuntimeError': [('        except Exception:\n', '        except (OSError, RuntimeError):\n')],
    '[독립 검토] narrow except RuntimeError': [('        except Exception:\n', '        except RuntimeError:\n')],
    '[독립 검토] success swallows OSError': [('    for handle in handles:\n        handle.close()\n    return result\n', '    for handle in handles:\n        try:\n            handle.close()\n        except OSError:\n            pass\n    return result\n')],
    '[독립 검토] success wraps in RuntimeError': [('    for handle in handles:\n        handle.close()\n    return result\n', '    for handle in handles:\n        try:\n            handle.close()\n        except Exception as exc:\n            raise RuntimeError("cleanup failed") from exc\n    return result\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] close quietly BaseException': [('        except Exception:\n', '        except BaseException:\n')],
    '[독립 검토] contextlib suppress': [('from collections.abc import Callable\nfrom typing import Protocol\n\n\nclass Closable(Protocol):\n    def close(self) -> None: ...\n\n\ndef _close_quietly(handles: list[Closable]) -> None:\n    for handle in handles:\n        try:\n            handle.close()\n        except Exception:\n            pass\n', 'import contextlib\nfrom collections.abc import Callable\nfrom typing import Protocol\n\n\nclass Closable(Protocol):\n    def close(self) -> None: ...\n\n\ndef _close_quietly(handles: list[Closable]) -> None:\n    for handle in handles:\n        with contextlib.suppress(Exception):\n            handle.close()\n')],
    '[독립 검토] else clause': [('    for handle in handles:\n        handle.close()\n    return result\n', '    else:\n        for handle in handles:\n            handle.close()\n        return result\n')],
    '[독립 검토] run except Exception': [('    except BaseException:\n', '    except Exception:\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
