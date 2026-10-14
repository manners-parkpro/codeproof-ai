from types import ModuleType
from asyncio import CancelledError


class StopCleanup(BaseException):
    pass


class Callback:
    def __init__(self, events, label, error=None, result=None):
        self.events = events
        self.label = label
        self.error = error
        self.result = result

    def __call__(self):
        self.events.append(self.label)
        if self.error is not None:
            raise self.error
        return self.result


class OrdinaryCallback(Callback):
    pass


def batch(mod, size, failed, error, result):
    stack = mod.CleanupStack()
    events = []
    for i in range(size):
        callback = OrdinaryCallback(events, i, error if i in failed else None, result)
        stack.register(callback)
    stack.drain()
    expected = list(range(size - 1, -1, -1))
    if events != expected:
        return True
    for _ in range(3):
        stack.drain()
        if events != expected:
            return True
    stack.register(Callback(events, "refill", error, result))
    stack.drain()
    stack.drain()
    return events != expected + ["refill"]


def duplicate_registrations(mod):
    class OrdinaryStack(mod.CleanupStack):
        pass

    stack = OrdinaryStack()
    events = []
    callback = Callback(events, "same", StopCleanup())
    stack.register(callback)
    stack.register(Callback(events, "middle"))
    stack.register(callback)
    stack.register(callback)
    stack.drain()
    stack.drain()
    return events != ["same", "same", "middle", "same"]


def registration_during_drain(mod, nested, error):
    stack = mod.CleanupStack()
    events = []
    entered = False

    def add_more():
        nonlocal entered
        events.append("register")
        if entered:
            return
        entered = True
        stack.register(Callback(events, "new-first", error))
        stack.register(Callback(events, "new-last", error))
        if nested:
            stack.drain()
        if error is not None:
            raise error

    stack.register(Callback(events, "old-first", error))
    stack.register(add_more)
    stack.register(Callback(events, "old-last", error))
    stack.drain()
    expected = ["old-last", "register"]
    if nested:
        expected += ["new-last", "new-first"]
    expected += ["old-first"]
    if events != expected:
        return True
    stack.drain()
    if not nested:
        expected += ["new-last", "new-first"]
    if events != expected:
        return True
    stack.drain()
    return events != expected


def empty_reentry(mod):
    stack = mod.CleanupStack()
    events = []
    entered = False

    def recurse():
        nonlocal entered
        events.append("enter")
        if not entered:
            entered = True
            stack.drain()
        events.append("exit")

    stack.register(Callback(events, "first"))
    stack.register(recurse)
    stack.drain()
    stack.drain()
    return events != ["enter", "exit", "first"]


def attack(mod: ModuleType) -> bool:
    errors = [
        ValueError("cleanup"),
        RuntimeError("cleanup"),
        BaseException("cleanup"),
        KeyboardInterrupt(),
        SystemExit(17),
        GeneratorExit(),
        CancelledError(),
        StopCleanup(),
        ExceptionGroup("cleanup", [ValueError(), RuntimeError()]),
        BaseExceptionGroup("cleanup", [KeyboardInterrupt(), SystemExit()]),
    ]
    try:
        for size in (0, 1, 2, 3, 8, 65, 257):
            if batch(mod, size, set(), None, object()):
                return True
            for failed in ({0}, {size // 2}, {size - 1}, set(range(size))):
                if batch(mod, size, failed, ValueError("cleanup"), None):
                    return True
        for error in errors:
            for failed in ({0}, {1}, {2}, {3}, {4}, set(range(5))):
                if batch(mod, 5, failed, error, None):
                    return True
        for result in (None, False, True, 0, 1, 10**1000, "", "done", [], [1], {}, {"ok": True}):
            if batch(mod, 4, set(), None, result):
                return True
        if duplicate_registrations(mod) or empty_reentry(mod):
            return True
        for nested in (False, True):
            for error in (None, ValueError("cleanup"), StopCleanup()):
                if registration_during_drain(mod, nested, error):
                    return True
    except BaseException:
        return True
    return False
