WEAKENED = {'복제 경계 우회': [('working = _snapshot(root)', 'working = root')],
 '루트만 복제하고 원본 목록 공유': [('def _snapshot(root: Node) -> Node:\n'
                        '    copies = {id(root): Node(root.label)}\n'
                        '    pending = [root]\n'
                        '    while pending:\n'
                        '        original = pending.pop()\n'
                        '        copied = copies[id(original)]\n'
                        '        for child in original.children:\n'
                        '            key = id(child)\n'
                        '            if key not in copies:\n'
                        '                copies[key] = Node(child.label)\n'
                        '                pending.append(child)\n'
                        '            copied.children.append(copies[key])\n'
                        '    return copies[id(root)]\n',
                        'def _snapshot(root: Node) -> Node:\n'
                        '    return Node(root.label, root.children)\n')],
 '목록만 복제하고 간선 대상 공유': [('def _snapshot(root: Node) -> Node:\n'
                        '    copies = {id(root): Node(root.label)}\n'
                        '    pending = [root]\n'
                        '    while pending:\n'
                        '        original = pending.pop()\n'
                        '        copied = copies[id(original)]\n'
                        '        for child in original.children:\n'
                        '            key = id(child)\n'
                        '            if key not in copies:\n'
                        '                copies[key] = Node(child.label)\n'
                        '                pending.append(child)\n'
                        '            copied.children.append(copies[key])\n'
                        '    return copies[id(root)]\n',
                        'def _snapshot(root: Node) -> Node:\n'
                        '    return Node(root.label, list(root.children))\n')],
 '라벨이 같은 서로 다른 노드 병합': [('copies = {id(root): Node(root.label)}',
                         'copies = {root.label: Node(root.label)}'),
                        ('copied = copies[id(original)]', 'copied = copies[original.label]'),
                        ('key = id(child)', 'key = child.label'),
                        ('return copies[id(root)]', 'return copies[root.label]')],
 '중복 간선 삭제': [('copied.children.append(copies[key])',
               'if copies[key] not in copied.children:\n'
               '                copied.children.append(copies[key])')],
 '순환 및 공유 노드 거절': [('if key in visited:\n            continue',
                    "if key in visited:\n            raise ValueError('repeated node')")],
 '간선 역순 누락': [('node.children.reverse()', 'node.children[:] = node.children')],
 '루트 외 라벨 변경 누락': [('node.label = prefix + node.label',
                    'node.label = prefix + node.label if node is root else node.label')],
 '한 노드 초과 허용': [('if len(visited) >= limit:', 'if len(visited) > limit:')],
 '정확한 경계 거절': [('if len(visited) >= limit:', 'if len(visited) + 1 >= limit:')],
 '음수 제한 무시': [('if len(visited) >= limit:', 'if limit >= 0 and len(visited) >= limit:')],
 '제한 제거': [('if len(visited) >= limit:', 'if False:')],
 'bool과 정수 하위 타입 거절': [('working = _snapshot(root)',
                        'if type(limit) is not int:\n'
                        "        raise TypeError('limit')\n"
                        '    working = _snapshot(root)')],
 '노드 하위 타입 거절': [('working = _snapshot(root)',
                  'if type(root) is not Node:\n'
                  "        raise TypeError('root')\n"
                  '    working = _snapshot(root)')],
 '문자열 Enum의 표현으로 치환': [('node.label = prefix + node.label',
                        "node.label = f'{prefix}{node.label}'")],
 '빈 접두사 변경': [('node.label = prefix + node.label',
               "node.label = (prefix or 'default:') + node.label")],
 '깊이에 제한 있는 재귀 복제': [('def _snapshot(root: Node) -> Node:\n'
                      '    copies = {id(root): Node(root.label)}\n'
                      '    pending = [root]\n'
                      '    while pending:\n'
                      '        original = pending.pop()\n'
                      '        copied = copies[id(original)]\n'
                      '        for child in original.children:\n'
                      '            key = id(child)\n'
                      '            if key not in copies:\n'
                      '                copies[key] = Node(child.label)\n'
                      '                pending.append(child)\n'
                      '            copied.children.append(copies[key])\n'
                      '    return copies[id(root)]\n',
                      'def _snapshot(root: Node) -> Node:\n'
                      '    copies = {}\n'
                      '    def visit(original):\n'
                      '        key = id(original)\n'
                      '        if key not in copies:\n'
                      '            copies[key] = Node(original.label)\n'
                      '            copies[key].children = [visit(child) for child in '
                      'original.children]\n'
                      '        return copies[key]\n'
                      '    return visit(root)\n')],
 '거절 전에 원본 부분 변경': [('working = _snapshot(root)',
                     'if limit < 2:\n'
                     '        root.label = prefix + root.label\n'
                     '    working = _snapshot(root)')],
 '복제 중 원본 간선 정렬 변경': [('for child in original.children:',
                       'original.children.reverse()\n        for child in original.children:')],
 '별도 자식 목록을 원본 목록으로 재연결': [('return copies[id(root)]',
                            'copies[id(root)].children = root.children\n'
                            '    return copies[id(root)]')]}

SAFE = {'거절 예외 타입 변경': [('raise ValueError("preview node limit exceeded")',
                  "raise RuntimeError('preview node limit exceeded')")],
 '간선 목록 갱신 방식 변경': [('node.children.reverse()', 'node.children[:] = reversed(node.children)')],
 '명시적 새 자식 목록': [('Node(root.label)', 'Node(root.label, [])'),
                 ('Node(child.label)', 'Node(child.label, [])')],
 '복제 탐색 순서 변경': [('original = pending.pop()', 'original = pending.pop(0)')],
 '방문 표 컨테이너 변경': [('visited = set()', 'visited = {}'), ('visited.add(key)', 'visited[key] = True')],
 '같은 경계식': [('if len(visited) >= limit:', 'if not len(visited) < limit:')],
 '반환 Node의 평범한 하위 클래스': [('def _snapshot(root: Node) -> Node:',
                          'class PreviewNode(Node):\n'
                          '    pass\n'
                          '\n'
                          '\n'
                          'def _snapshot(root: Node) -> Node:'),
                         ('Node(root.label)', 'PreviewNode(root.label)'),
                         ('Node(child.label)', 'PreviewNode(child.label)')]}

RACY = {}
