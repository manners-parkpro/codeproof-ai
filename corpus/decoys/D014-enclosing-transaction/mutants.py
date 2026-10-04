"""D014 변이 - 독립 검토 12개 · 재확인 12개 (약화 7 · 안전 5 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] alias snapshot': [('        snapshot = dict(self.balances)\n', '        snapshot = self.balances\n')],
    '[독립 검토] no restore': [('            self.balances.clear()\n            self.balances.update(snapshot)\n', '')],
    '[독립 검토] rebind copy': [('            self.balances.clear()\n            self.balances.update(snapshot)\n', '            self.balances = dict(snapshot)\n')],
    '[독립 검토] rebind snapshot': [('            self.balances.clear()\n            self.balances.update(snapshot)\n', '            self.balances = snapshot\n')],
    '[독립 검토] restore drop zero': [('            self.balances.update(snapshot)\n', '            self.balances.update({k: v for k, v in snapshot.items() if v})\n')],
    '[독립 검토 · 재확인 뒤 약화] KeyError 만 잡아 되돌림 (기본값 팩터리의 ValueError 가 지나간다)': [('        except Exception:\n', '        except KeyError:\n')],
    '[독립 검토 · 재확인 뒤 약화] clear 없이 update (실패 전에 생긴 계정이 남는다)': [('            self.balances.clear()\n', '')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] copy method': [('        snapshot = dict(self.balances)\n', '        snapshot = self.balances.copy()\n')],
    '[독립 검토] except BaseException': [('        except Exception:\n', '        except BaseException:\n')],
    '[독립 검토] ior': [('            self.balances.update(snapshot)\n', '            self.balances |= snapshot\n')],
    '[독립 검토] 없는 계정을 미리 LookupError 로 거절': [('    if amount <= 0:\n        raise ValueError(amount)\n', '    if amount <= 0:\n        raise ValueError(amount)\n    if src not in ledger.balances or dst not in ledger.balances:\n        raise LookupError(f"unknown account: {src!r} -> {dst!r}")\n')],
    '[독립 검토] 되돌린 뒤 도메인 예외로 감싸 올림': [('        except Exception:\n', '        except Exception as exc:\n'), ('            raise\n', '            raise TransferError("transfer rolled back") from exc\n'), ('        _move(ledger, src, dst, amount)\n', '        _move(ledger, src, dst, amount)\n\n\nclass TransferError(Exception):\n    pass\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
