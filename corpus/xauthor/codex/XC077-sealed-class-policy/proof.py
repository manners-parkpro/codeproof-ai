"""정책 변경 공격 - 각 변경 시도 직후 공개 정책과 작업자 수 계약을 검사한다."""

from enum import IntEnum
import operator
from types import ModuleType


class PlainInt(int):
    pass


class Counts(IntEnum):
    NEGATIVE = -9
    ZERO = 0
    LOWER = 2
    MIDDLE = 31
    UPPER = 64
    EXCESS = 65


VALUES = (
    -(10**400), -65, -9, -1, 0, 1, 2, 3, 31, 63, 64, 65, 10**400,
    False, True,
    *(PlainInt(n) for n in (-10**400, -1, 0, 2, 3, 63, 64, 65, 10**400)),
    *Counts,
)


def broken(mod: ModuleType) -> bool:
    try:
        current = mod.policy()
        if current.min_workers != 2 or current.max_workers != 64:
            return True
        for backlog in VALUES:
            expected = 2 if backlog < 2 else 64 if backlog > 64 else backlog
            if mod.worker_count(backlog) != expected:
                return True
    except Exception:
        return True
    return False


def checked(mod: ModuleType, operation, *args) -> bool:
    try:
        operation(*args)
    except Exception:
        pass
    return broken(mod)


def augment(target, name, amount) -> None:
    setattr(target, name, getattr(target, name) + amount)


def subtract(target, name, amount) -> None:
    setattr(target, name, getattr(target, name) - amount)


def merge(target, changes) -> None:
    target |= changes


def mapping_attack(mod: ModuleType, target) -> bool:
    for name in ("min_workers", "max_workers"):
        for value in VALUES:
            for operation in (
                lambda: operator.setitem(target, name, value),
                lambda: target.update({name: value}),
                lambda: target.setdefault(name, value),
                lambda: merge(target, {name: value}),
            ):
                if checked(mod, operation):
                    return True
        for operation in (
            lambda: operator.delitem(target, name),
            lambda: target.pop(name),
            lambda: target.setdefault(name, -9),
        ):
            if checked(mod, operation):
                return True
    for operation in (lambda: target.popitem(), lambda: target.clear()):
        if checked(mod, operation):
            return True
    return False


def attack(mod: ModuleType) -> bool:
    if broken(mod):
        return True
    for target in (mod.LIMITS, mod.policy()):
        for name in ("min_workers", "max_workers"):
            for value in VALUES:
                if checked(mod, setattr, target, name, value):
                    return True
                if checked(mod, augment, target, name, value):
                    return True
                if checked(mod, subtract, target, name, value):
                    return True
            if checked(mod, delattr, target, name):
                return True
        for namespace in (target.__dict__, vars(target)):
            if mapping_attack(mod, namespace):
                return True
    if mapping_attack(mod, mod.BOOTSTRAP):
        return True
    for source in (mod.LIMITS, mod.policy()):
        for namespace in ({}, {"min_workers": -9, "max_workers": 999}):
            try:
                derived = type("LocalLimits", (source,), namespace)
            except Exception:
                if broken(mod):
                    return True
                continue
            if broken(mod):
                return True
            for cls in (source, derived):
                try:
                    instance = cls()
                except Exception:
                    if broken(mod):
                        return True
                    continue
                if broken(mod):
                    return True
                for name in ("min_workers", "max_workers"):
                    for value in VALUES:
                        if checked(mod, setattr, instance, name, value):
                            return True
                        if checked(mod, augment, instance, name, value):
                            return True
                        if checked(mod, subtract, instance, name, value):
                            return True
                    if checked(mod, delattr, instance, name):
                        return True
    return broken(mod)
