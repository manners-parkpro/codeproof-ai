"""워크플로 그래프 미리보기 - 정체성별 복제로 순환과 공유 노드를 분리한다."""

from dataclasses import dataclass, field


@dataclass(eq=False)
class Node:
    label: str
    children: list["Node"] = field(default_factory=list)


def _snapshot(root: Node) -> Node:
    copies = {id(root): Node(root.label)}
    pending = [root]
    while pending:
        original = pending.pop()
        copied = copies[id(original)]
        for child in original.children:
            key = id(child)
            if key not in copies:
                copies[key] = Node(child.label)
                pending.append(child)
            copied.children.append(copies[key])
    return copies[id(root)]


def _decorate(root: Node, prefix: str, limit: int) -> Node:
    visited = set()
    pending = [root]
    while pending:
        node = pending.pop()
        key = id(node)
        if key in visited:
            continue
        if len(visited) >= limit:
            raise ValueError("preview node limit exceeded")
        visited.add(key)
        node.label = prefix + node.label
        node.children.reverse()
        pending.extend(node.children)
    return root


def preview(root: Node, prefix: str, limit: int) -> Node:
    working = _snapshot(root)
    return _decorate(working, prefix, limit)
