from enum import Enum, IntEnum
from random import Random
from types import ModuleType


class Text(str):
    pass


class Label(str, Enum):
    READY = "ready"


class Edges(list):
    pass


class Limit(int):
    pass


class Budget(IntEnum):
    ZERO = 0
    ONE = 1
    TEN = 10


def _records(root):
    records = {}
    pending = [root]
    while pending:
        node = pending.pop()
        if id(node) in records:
            continue
        records[id(node)] = (node, node.label, node.children, tuple(node.children))
        pending.extend(node.children)
    return records


def _unchanged(records):
    for node, label, children, targets in records.values():
        if node.label != label or node.children is not children:
            return False
        if len(children) != len(targets):
            return False
        if any(a is not b for a, b in zip(children, targets)):
            return False
    return True


def _matches(root, result, records, prefix):
    originals = set(records)
    original_lists = {id(row[2]) for row in records.values()}
    mapping = {}
    reverse = {}
    pending = [(root, result)]
    while pending:
        original, copied = pending.pop()
        key = id(original)
        if key in mapping:
            if mapping[key] is not copied:
                return False
            continue
        if id(copied) in originals or id(copied) in reverse:
            return False
        if id(copied.children) in original_lists:
            return False
        mapping[key] = copied
        reverse[id(copied)] = original
        _, label, _, targets = records[key]
        if copied.label != prefix + label:
            return False
        if len(copied.children) != len(targets):
            return False
        pending.extend(zip(reversed(targets), copied.children))
    return len(mapping) == len(records)


def _mutate(records, mod):
    for node, _, _, _ in records.values():
        node.label = "changed"
        node.children.append(mod.Node("new"))
        node.children.reverse()
        node.children[:1] = [mod.Node("replacement")]
        del node.children[-1:]
        node.children = [mod.Node("reassigned")]


def _build(mod, rows, variant, shared):
    class DerivedNode(mod.Node):
        pass

    node_type = DerivedNode if variant else mod.Node
    edge_type = Edges if variant else list
    labels = ("same", "same", "", "한글", Text("text"), Label.READY)
    nodes = [node_type(labels[i % len(labels)]) for i in range(len(rows))]
    for node, row in zip(nodes, rows):
        node.children = edge_type(nodes[index] for index in row)
    if shared:
        nodes[1].children = nodes[0].children
    return nodes[0]


def _case(mod, rows, variant, shared, prefix, limit):
    root = _build(mod, rows, variant, shared)
    before = _records(root)
    result = None
    rejected = False
    try:
        result = mod.preview(root, prefix, limit)
    except Exception:
        rejected = True
    if not _unchanged(before):
        return True
    expected_rejection = len(before) > limit
    if rejected != expected_rejection:
        return True
    if rejected:
        return False
    if not _matches(root, result, before, prefix):
        return True
    returned = _records(result)
    _mutate(before, mod)
    if not _unchanged(returned):
        return True
    changed_original = _records(root)
    changed_original.update({key: (row[0], row[0].label, row[0].children,
                                  tuple(row[0].children))
                             for key, row in before.items()})
    _mutate(returned, mod)
    return not _unchanged(changed_original)


def attack(mod: ModuleType) -> bool:
    shapes = [
        ([[]], False),
        ([[0]], False),
        ([[0, 0]], False),
        ([[1], [0]], False),
        ([[1, 2], [], []], False),
        ([[1, 2], [3], [3], []], False),
        ([[1, 1, 2], [2, 0], [1]], False),
        ([[1, 2], [1, 2], []], True),
        ([[1], [], [2]], False),
    ]
    rng = Random(44044)
    for size in (2, 3, 5, 9, 17):
        for _ in range(6):
            rows = [[rng.randrange(size) for _ in range(rng.randrange(5))]
                    for _ in range(size)]
            shapes.append((rows, False))
    prefixes = ("", "view:", Text("하나:"), Label.READY, "\\x00")
    for rows, shared in shapes:
        size = len(rows)
        limits = (-10**100, -1, 0, 1, size - 1, size, size + 1, 10**100,
                  False, True, Limit(size), Budget.ZERO, Budget.ONE, Budget.TEN)
        for variant in (False, True):
            for prefix in prefixes:
                for limit in limits:
                    if _case(mod, rows, variant, shared, prefix, limit):
                        return True
    for size in (1200, 4096):
        rows = [[i + 1] for i in range(size - 1)] + [[]]
        for limit in (0, 1, size - 1, size, 10**100):
            if _case(mod, rows, True, False, "deep:", limit):
                return True
        rows[-1] = [0, size // 2]
        if _case(mod, rows, False, False, "", size):
            return True
    return False
