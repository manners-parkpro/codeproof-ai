"""주장 축별 변이 - 경계와 값 의미의 약화 및 동등한 구현을 비교한다."""

WEAKENED = {'정규화 우회로 상한 제거': [('    bounds = slice(start, stop, step).indices(256)',
                    '    bounds = (start, stop, step)')],
 '끝 슬롯 누락': [('    bounds = slice(start, stop, step).indices(256)',
              '    bounds = slice(start, stop, step).indices(255)')],
 '상한 하나 초과': [('    bounds = slice(start, stop, step).indices(256)',
               '    bounds = slice(start, stop, step).indices(257)')],
 '음수 시작점의 상대 위치 무시': [('    bounds = slice(start, stop, step).indices(256)',
                       '    bounds = slice(max(0, start), stop, step).indices(256)')],
 '음수 끝점의 상대 위치 무시': [('    bounds = slice(start, stop, step).indices(256)',
                      '    bounds = slice(start, max(0, stop), step).indices(256)')],
 '역방향을 정방향으로 변경': [('    bounds = slice(start, stop, step).indices(256)',
                    '    bounds = slice(start, stop, abs(step)).indices(256)')],
 '간격을 한 칸으로 축소': [('    bounds = slice(start, stop, step).indices(256)',
                   '    bounds = slice(start, stop, -1 if step < 0 else 1).indices(256)')],
 '0 간격을 기본 간격으로 수용': [('    bounds = slice(start, stop, step).indices(256)',
                       '    bounds = slice(start, stop, step or 1).indices(256)')],
 '큰 정수 좌표를 기계 정수로 제한': [('    bounds = slice(start, stop, step).indices(256)',
                         '    if abs(start) > 2**63 - 1 or abs(stop) > 2**63 - 1:\n'
                         '        raise ValueError\n'
                         '    bounds = slice(start, stop, step).indices(256)')],
 '큰 간격을 슬롯 수 미만으로 절단': [('    bounds = slice(start, stop, step).indices(256)',
                         '    bounds = slice(start, stop, max(-255, min(255, step))).indices(256)')],
 'bool 입력을 별도로 거절': [('    bounds = slice(start, stop, step).indices(256)',
                      '    if any(isinstance(x, bool) for x in (start, stop, step)):\n'
                      '        raise TypeError\n'
                      '    bounds = slice(start, stop, step).indices(256)')],
 'IntEnum 입력을 별도로 거절': [('    bounds = slice(start, stop, step).indices(256)',
                         '    from enum import IntEnum\n'
                         '    if any(isinstance(x, IntEnum) for x in (start, stop, step)):\n'
                         '        raise TypeError\n'
                         '    bounds = slice(start, stop, step).indices(256)')],
 '일반 int 하위 클래스를 거절': [('    bounds = slice(start, stop, step).indices(256)',
                        '    from enum import IntEnum, IntFlag\n'
                        '    if any(type(x) not in (int, bool) and not isinstance(x, (IntEnum, IntFlag)) for '
                        'x in (start, stop, step)):\n'
                        '        raise TypeError\n'
                        '    bounds = slice(start, stop, step).indices(256)')],
 '값을 한 슬롯씩 이동': [('    return list(range(start, stop, step))',
                  '    return [i + 1 for i in range(start, stop, step)]')],
 '슬롯 순서 반전': [('    return list(range(start, stop, step))',
               '    return list(reversed(range(start, stop, step)))')],
 '빈 구간에 기본 슬롯 삽입': [('    return list(range(start, stop, step))',
                     '    return list(range(start, stop, step)) or [0]')],
 '첫 호출 좌표를 다음 호출에도 재사용': [('    bounds = slice(start, stop, step).indices(256)',
                           '    global _saved_bounds\n'
                           "    if '_saved_bounds' not in globals():\n"
                           '        _saved_bounds = slice(start, stop, step).indices(256)\n'
                           '    bounds = _saved_bounds')],
 '최적화 모드에서 정규화 소실': [('    bounds = slice(start, stop, step).indices(256)',
                      '    bounds = (start, stop, step)\n'
                      '    assert (bounds := slice(start, stop, step).indices(256))')],
 '0 간격 검사만 assert로 이동': [('    bounds = slice(start, stop, step).indices(256)',
                          '    assert step != 0\n    bounds = slice(start, stop, step or 1).indices(256)')],
 '기본 간격을 변경': [('step: int = 1) -> Sequence[int]:', 'step: int = 2) -> Sequence[int]:')]}

SAFE = {'튜플 반환': [('    return list(range(start, stop, step))', '    return tuple(range(start, stop, step))')],
 'range 시퀀스 반환': [('    return list(range(start, stop, step))', '    return range(start, stop, step)')],
 '0 간격의 예외 종류 변경': [('    bounds = slice(start, stop, step).indices(256)',
                     '    if step == 0:\n'
                     "        raise TypeError('zero stride')\n"
                     '    bounds = slice(start, stop, step).indices(256)')],
 '0 간격의 다른 동기 예외': [('    bounds = slice(start, stop, step).indices(256)',
                     '    if step == 0:\n'
                     "        raise RuntimeError('zero stride')\n"
                     '    bounds = slice(start, stop, step).indices(256)')],
 '정수 하위 타입을 기본 정수로 변환': [('    bounds = slice(start, stop, step).indices(256)',
                          '    bounds = slice(int(start), int(stop), int(step)).indices(256)')],
 '슬롯 수의 동등 표현': [('    bounds = slice(start, stop, step).indices(256)',
                  '    bounds = slice(start, stop, step).indices(len(range(256)))')],
 '하위 함수 대신 직접 물질화': [('    return _materialize(*bounds)', '    return tuple(range(*bounds))')],
 '슬롯 목록을 직접 슬라이싱': [('    bounds = slice(start, stop, step).indices(256)\n    return _materialize(*bounds)',
                     '    return list(range(256))[start:stop:step]')],
 'Sequence import 형태 변경': [('from collections.abc import Sequence', 'from typing import Sequence')],
 '방향별 경계 연산으로 정규화': [('    bounds = slice(start, stop, step).indices(256)',
                      '    if step == 0:\n'
                      "        raise ValueError('zero stride')\n"
                      '    low, high = (0, 256) if step > 0 else (-1, 255)\n'
                      '    first = start + 256 if start < 0 else start\n'
                      '    last = stop + 256 if stop < 0 else stop\n'
                      '    bounds = (min(high, max(low, first)), min(high, max(low, last)), step)')]}

RACY = {}
