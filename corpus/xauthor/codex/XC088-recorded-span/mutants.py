WEAKENED = {'누락 표식 통과': [('return value is not None', 'return True')],
 '0을 누락으로 취급': [('return value is not None', 'return bool(value)')],
 '음수 제외': [('return value is not None', 'return value is not None and value >= 0')],
 'bool 제외': [('return value is not None',
              'return value is not None and not isinstance(value, bool)')],
 'IntEnum 제외': [('from typing import TypeGuard',
                 'from typing import TypeGuard\nfrom enum import IntEnum'),
                ('return value is not None',
                 'return value is not None and not isinstance(value, IntEnum)')],
 '사용자 정수 하위 타입 제외': [('from typing import TypeGuard',
                      'from typing import TypeGuard\nfrom enum import IntEnum'),
                     ('return value is not None',
                      'return value is not None and (type(value) in (int, bool) or '
                      'isinstance(value, IntEnum))')],
 '목록 하위 타입 거절': [('recorded = tuple(filter(_is_recorded, samples))',
                  'if type(samples) is not list:\n'
                  '        raise TypeError\n'
                  '    recorded = tuple(filter(_is_recorded, samples))')],
 '정수를 signed64로 제한': [('return value is not None',
                       'return value is not None and -(1 << 63) <= value < (1 << 63)')],
 '첫 원소 누락': [('recorded = tuple(filter(_is_recorded, samples))',
              'recorded = tuple(filter(_is_recorded, samples[1:]))')],
 '긴 입력 뒤쪽 누락': [('recorded = tuple(filter(_is_recorded, samples))',
                 'recorded = tuple(filter(_is_recorded, samples[:1024]))')],
 '긴 입력 앞쪽 누락': [('recorded = tuple(filter(_is_recorded, samples))',
                 'recorded = tuple(filter(_is_recorded, samples[-1024:]))')],
 '빈 입력 가드 제거': [('    if not recorded:\n        return None\n', '')],
 '빈 입력은 0': [('if not recorded:\n        return None', 'if not recorded:\n        return 0')],
 '단일 값은 None': [('if not recorded:', 'if len(recorded) < 2:')],
 '동일한 여러 값은 None': [('return max(recorded) - min(recorded)',
                     'return None if len(recorded) > 1 and max(recorded) == min(recorded) else '
                     'max(recorded) - min(recorded)')],
 '뺄셈 순서 반전': [('return max(recorded) - min(recorded)', 'return min(recorded) - max(recorded)')],
 '최솟값 무시': [('return max(recorded) - min(recorded)', 'return max(recorded)')],
 '입력 순서에 의존': [('return max(recorded) - min(recorded)', 'return recorded[-1] - recorded[0]')],
 '실수 반환': [('return max(recorded) - min(recorded)', 'return float(max(recorded) - min(recorded))')],
 '큰 정수의 실수 반올림': [('return max(recorded) - min(recorded)',
                   'return int(float(max(recorded)) - float(min(recorded)))')],
 '입력 순서 변경': [('recorded = tuple(filter(_is_recorded, samples))',
               'samples.reverse()\n    recorded = tuple(filter(_is_recorded, samples))')],
 '입력 누락 원소 삭제': [('recorded = tuple(filter(_is_recorded, samples))',
                  'samples[:] = [value for value in samples if value is not None]\n'
                  '    recorded = tuple(filter(_is_recorded, samples))')],
 '입력 원소를 int로 교체': [('recorded = tuple(filter(_is_recorded, samples))',
                     'samples[:] = [int(value) if value is not None else None for value in '
                     'samples]\n'
                     '    recorded = tuple(filter(_is_recorded, samples))')],
 '이전 호출 결과 재사용': [('from typing import TypeGuard',
                   'from typing import TypeGuard\n\n_previous = None'),
                  ('return max(recorded) - min(recorded)',
                   'global _previous\n'
                   '    if _previous is None:\n'
                   '        _previous = max(recorded) - min(recorded)\n'
                   '    return _previous')],
 '같은 목록의 변경을 무시': [('from typing import TypeGuard', 'from typing import TypeGuard\n\n_cache = {}'),
                   ('recorded = tuple(filter(_is_recorded, samples))',
                    'recorded = _cache.setdefault(id(samples), tuple(filter(_is_recorded, '
                    'samples)))')]}

SAFE = {'정수 isinstance 판별': [('return value is not None', 'return isinstance(value, int)')],
 '부정한 동일성 판별': [('return value is not None', 'return not (value is None)')],
 'TypeGuard 대신 bool 주석': [('def _is_recorded(value: int | None) -> TypeGuard[int]:',
                           'def _is_recorded(value: int | None) -> bool:')],
 '중간 컨테이너 목록': [('recorded = tuple(filter(_is_recorded, samples))',
                 'recorded = list(filter(_is_recorded, samples))')],
 '컴프리헨션으로 선택': [('recorded = tuple(filter(_is_recorded, samples))',
                 'recorded = tuple(value for value in samples if _is_recorded(value))')],
 '정렬된 복사본의 양 끝': [('recorded = tuple(filter(_is_recorded, samples))',
                   'recorded = sorted(filter(_is_recorded, samples))'),
                  ('return max(recorded) - min(recorded)', 'return recorded[-1] - recorded[0]')],
 '정수 기본형으로 정규화한 복사본': [('recorded = tuple(filter(_is_recorded, samples))',
                        'recorded = tuple(int(value) for value in samples if '
                        '_is_recorded(value))')],
 '단일 값 빠른 반환': [('return max(recorded) - min(recorded)',
                 'return 0 if len(recorded) == 1 else max(recorded) - min(recorded)')],
 'import 별칭': [('from typing import TypeGuard', 'from typing import TypeGuard as Narrowed'),
               ('-> TypeGuard[int]:', '-> Narrowed[int]:')]}

RACY = {}
