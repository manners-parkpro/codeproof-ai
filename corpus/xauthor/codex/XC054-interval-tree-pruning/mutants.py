"""주장의 각 축을 약화한 변이와 관찰 결과를 보존하는 변형."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "끝점이 질의 시작점에 닿는 리프 포함": [
        ("node.upper <= start", "node.upper < start"),
    ],
    "시작점이 질의 끝점에 닿는 리프 포함": [
        ("node.lower >= stop", "node.lower > stop"),
    ],
    "오른쪽 배제 검사 제거": [
        ("node.upper <= start or node.lower >= stop", "node.upper <= start"),
    ],
    "왼쪽 배제 검사 제거": [
        ("node.upper <= start or node.lower >= stop", "node.lower >= stop"),
    ],
    "한 칸 겹치는 왼쪽 경계 누락": [
        ("node.upper <= start", "node.upper <= start + 1"),
    ],
    "한 칸 겹치는 오른쪽 경계 누락": [
        ("node.lower >= stop", "node.lower >= stop - 1"),
    ],
    "빈 질의 조기 반환 제거": [
        ("if start == stop or not nodes:", "if not nodes:"),
    ],
    "빈 행을 트리에 포함": [
        ("if lower < upper]", "if lower <= upper]"),
    ],
    "질의 역전 검사 제거": [
        ("start > stop or any(lower > upper for lower, upper in spans)", "any(lower > upper for lower, upper in spans)"),
    ],
    "행 역전 검사 제거": [
        ("start > stop or any(lower > upper for lower, upper in spans)", "start > stop"),
    ],
    "마지막 행 역전 검사 생략": [
        ("any(lower > upper for lower, upper in spans)", "any(lower > upper for lower, upper in spans[:-1])"),
    ],
    "빈 질의로 잘못된 행 검증 우회": [
        ("    if start > stop or any(", "    if start == stop:\n        return []\n    if start > stop or any("),
    ],
    "빈 입력으로 잘못된 질의 검증 우회": [
        ("    if start > stop or any(", "    if not spans:\n        return []\n    if start > stop or any("),
    ],
    "내부 최소 시작점 대신 최대 사용": [
        ("min(left.lower, right.lower)", "max(left.lower, right.lower)"),
    ],
    "내부 최대 끝점 대신 최소 사용": [
        ("max(left.upper, right.upper)", "min(left.upper, right.upper)"),
    ],
    "오른쪽 자손의 끝점 요약 누락": [
        ("max(left.upper, right.upper)", "left.upper"),
    ],
    "왼쪽 자손의 시작점 요약 누락": [
        ("min(left.lower, right.lower)", "right.lower"),
    ],
    "행 번호 0을 비리프로 취급": [
        ("if node.row is not None:", "if node.row:"),
    ],
    "같은 행을 두 번 추가": [
        ("result.append(node.row)", "result.extend([node.row, node.row])"),
    ],
    "반환 순서 뒤집기": [
        ("    return result\n", "    return result[::-1]\n"),
    ],
    "오른쪽 자손 방문 생략": [
        ("    if node.right is not None:\n", "    if False:\n"),
    ],
    "빈 행 제거 후 행 번호 재부여": [
        ("enumerate(spans) if lower < upper", "enumerate((a, b) for a, b in spans if a < b)"),
    ],
    "성공 때 입력을 정렬": [
        ("    nodes = [_Node", "    spans.sort()\n    nodes = [_Node"),
    ],
    "거절 때 입력 삭제": [
        ("        raise ValueError(\"reversed interval\")", "        spans.clear()\n        raise ValueError(\"reversed interval\")"),
    ],
    "중복 행 제거": [
        ("enumerate(spans)", "enumerate(dict.fromkeys(spans))"),
    ],
    "큰 정수를 실수로 축소": [
        ("    nodes = [_Node", "    start, stop = float(start), float(stop)\n    nodes = [_Node"),
    ],
    "음수 좌표를 절댓값으로 변환": [
        ("    nodes = [_Node", "    start, stop = abs(start), abs(stop)\n    nodes = [_Node"),
    ],
    "정확한 int만 허용": [
        ("    nodes = [_Node", "    if type(start) is not int or type(stop) is not int or any(type(v) is not int for pair in spans for v in pair):\n        raise TypeError(\"int only\")\n    nodes = [_Node"),
    ],
    "정확한 list와 tuple만 허용": [
        ("    nodes = [_Node", "    if type(spans) is not list or any(type(pair) is not tuple for pair in spans):\n        raise TypeError(\"plain containers only\")\n    nodes = [_Node"),
    ],
    "큰 트리에서 일부 리프만 사용": [
        ("_collect(_build(nodes), start, stop, result)", "_collect(_build(nodes[:64]), start, stop, result)"),
    ],
    "검증을 assert로 약화": [
        ("    if start > stop or any(lower > upper for lower, upper in spans):\n        raise ValueError(\"reversed interval\")", "    assert start <= stop and all(lower <= upper for lower, upper in spans)"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "거절 예외 종류 변경": [
        ("raise ValueError(\"reversed interval\")", "raise RuntimeError(\"reversed interval\")"),
    ],
    "동등한 정수 경계식": [
        ("node.upper <= start or node.lower >= stop", "node.upper < start + 1 or node.lower > stop - 1"),
    ],
    "드모르간 가지치기": [
        ("node.upper <= start or node.lower >= stop", "not (node.upper > start and node.lower < stop)"),
    ],
    "입력 정수 하위 타입 정규화": [
        ("    nodes = [_Node", "    start, stop = int(start), int(stop)\n    spans = [(int(a), int(b)) for a, b in spans]\n    nodes = [_Node"),
    ],
    "내부 노드 목록을 튜플로 변경": [
        ("_collect(_build(nodes), start, stop, result)", "_collect(_build(tuple(nodes)), start, stop, result)"),
    ],
    "트리 분할 크기 변경": [
        ("middle = len(nodes) // 2", "middle = (len(nodes) + 1) // 2"),
    ],
    "결과 리스트 하위 타입": [
        ("    result: list[int] = []", "    class Rows(list):\n        pass\n    result: list[int] = Rows()"),
    ],
    "최솟값 최댓값 인수 순서 변경": [
        ("min(left.lower, right.lower)", "min(right.lower, left.lower)"),
        ("max(left.upper, right.upper)", "max(right.upper, left.upper)"),
    ],
    "dataclass import 형태 변경": [
        ("from dataclasses import dataclass", "import dataclasses"),
        ("@dataclass(frozen=True)", "@dataclasses.dataclass(frozen=True)"),
    ],
    "입력을 읽기 전용 사본으로 대체": [
        ("    if start > stop or any(", "    spans = list(spans)\n    if start > stop or any("),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
