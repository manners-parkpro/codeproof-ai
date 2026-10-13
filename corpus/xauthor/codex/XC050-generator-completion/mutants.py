WEAKENED: dict[str, list[tuple[str, str]]] = {'완료 값을 반복 채널로 노출': [('    return "run", command', '    yield "run", command')],
 '빈 labels': [('    return "run", command',
               '    if not labels:\n        yield "run", command\n    return "run", command')],
 '단일 labels': [('    return "run", command',
                '    if len(labels) == 1:\n        yield "run", command\n    return "run", command')],
 '긴 labels': [('    return "run", command',
               '    if len(labels) > 1024:\n        yield "run", command\n    return "run", command')],
 '빈 command': [('    return "run", command',
                '    if command == "":\n        yield "run", command\n    return "run", command')],
 '긴 command': [('    return "run", command',
                '    if len(command) > 65536:\n        yield "run", command\n    return "run", command')],
 'command 하위 타입': [('    return "run", command',
                    '    if type(command) is not str:\n'
                    '        yield "run", command\n'
                    '    return "run", command')],
 'labels 하위 타입': [('    return "run", command',
                   '    if type(labels) is not list:\n'
                   '        yield "run", command\n'
                   '    return "run", command')],
 'label 원소 하위 타입': [('    return "run", command',
                     '    if any(type(label) is not str for label in labels):\n'
                     '        yield "run", command\n'
                     '    return "run", command')],
 'command 줄바꿈': [('    return "run", command',
                  '    if "\\n" in command:\n        yield "run", command\n    return "run", command')],
 'command NUL': [('    return "run", command',
                  '    if "\\x00" in command:\n        yield "run", command\n    return "run", command')],
 'command 실행 태그': [('    return "run", command',
                    '    if command == "run":\n        yield "run", command\n    return "run", command')],
 '입력 원소를 이벤트 태그로 사용': [('        yield "display", label', '        yield label, label')],
 'yield from으로 완료 값 전달': [('    return "run", command', '    yield from (("run", command),)')],
 '최적화에서 사라지는 assert': [('    return "run", command',
                        '    assert False, ("run", command)\n    yield "run", command')],
 '소비자가 완료 지시를 직접 덧붙임': [('for kind, value in _plan(command, labels):',
                         'for kind, value in (*_plan(command, labels), ("run", command)):')]}

SAFE: dict[str, list[tuple[str, str]]] = {'이벤트 컨테이너를 list로 변경': [('yield "display", label', 'yield ["display", label]')],
 '표시 태그 이름 변경': [('yield "display", label', 'yield "notice", label')],
 '완료 값 제거': [('    return "run", command', '    return None')],
 '완료 값 컨테이너 변경': [('    return "run", command', '    return ["run", command]')],
 '빈 명령 ValueError 거절': [('    for label in labels:',
                         '    if command == "":\n'
                         '        raise ValueError("empty command")\n'
                         '    for label in labels:')],
 '빈 명령 RuntimeError 거절': [('    for label in labels:',
                           '    if command == "":\n'
                           '        raise RuntimeError("empty command")\n'
                           '    for label in labels:')],
 '모듈 import 별칭': [('import subprocess', 'import subprocess as processes'),
                  ('subprocess.run(value, shell=True, check=True)',
                   'processes.run(value, shell=True, check=True)')],
 '함수 직접 import': [('import subprocess', 'from subprocess import run as launch'),
                  ('subprocess.run(value, shell=True, check=True)', 'launch(value, shell=True, check=True)')],
 '실행 결과 검사 설정 변경': [('check=True', 'check=False')]}

RACY: dict[str, list[tuple[str, str]]] = {}
