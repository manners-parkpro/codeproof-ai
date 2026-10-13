"""정리 큐 변이 - 주장 축마다 약화와 안전한 표현 변경을 대조한다."""

WEAKENED = {'초기 상태: 유령 등록': [('self._pending: list[object] = []', 'self._pending: list[object] = [object()]')],
 '등록 순서: 앞에 삽입': [('        self._pending.append(resource)\n\n    @property',
                   '        self._pending.insert(0, resource)\n\n    @property')],
 '동일 객체 중복: 등록 합치기': [('        self._pending.append(resource)\n\n    @property',
                       '        if not any(item is resource for item in self._pending):\n'
                       '            self._pending.append(resource)\n'
                       '\n'
                       '    @property')],
 '동등한 다른 객체: 등록 합치기': [('        self._pending.append(resource)\n\n    @property',
                        '        if resource not in self._pending:\n'
                        '            self._pending.append(resource)\n'
                        '\n'
                        '    @property')],
 '모든 object: 거짓 값 누락': [('        self._pending.append(resource)\n\n    @property',
                         '        if resource:\n'
                         '            self._pending.append(resource)\n'
                         '\n'
                         '    @property')],
 '모든 object: 평범한 하위 타입 누락': [('        self._pending.append(resource)\n\n    @property',
                              '        if type(resource) not in (str, list) and '
                              'isinstance(resource, (str, list)):\n'
                              '            return\n'
                              '        self._pending.append(resource)\n'
                              '\n'
                              '    @property')],
 '크기 양화: 등록 상한': [('        self._pending.append(resource)\n\n    @property',
                   '        if len(self._pending) < 32:\n'
                   '            self._pending.append(resource)\n'
                   '\n'
                   '    @property')],
 '객체 동일성: 등록 복사': [('        self._pending.append(resource)\n\n    @property',
                    '        from copy import copy\n'
                    '        self._pending.append(copy(resource))\n'
                    '\n'
                    '    @property')],
 '스냅샷 독립성: 내부 목록 반환': [('return tuple(self._pending)', 'return self._pending')],
 '스냅샷 순서: 역순': [('return tuple(self._pending)', 'return tuple(reversed(self._pending))')],
 '호출 순서: 역순 방문': [('for resource in batch:', 'for resource in reversed(batch):')],
 '정확히 한 번: 중복 호출': [('                dispose(resource)',
                     '                dispose(resource)\n                dispose(resource)')],
 '크기 양화: 순회 상한': [('for resource in batch:', 'for resource in batch[:32]:')],
 '빈 상태: 성공 수 하나': [('        completed = 0', '        completed = 1')],
 '성공 항목 제거: 모든 항목 보관': [('                if not released:', '                if True:')],
 '실패 항목 보관: 가드 우회': [('                if not released:', '                if False:')],
 '매 항목 초기화: 앞선 성공 잔류': [('        for resource in batch:\n            released = False',
                         '        released = False\n        for resource in batch:')],
 '반환값 무관: 진리값을 성공으로 사용': [('                dispose(resource)\n                released = True',
                           '                released = bool(dispose(resource))')],
 '반환값 무관: 예외 객체 반환을 실패로 사용': [('                dispose(resource)\n                released = True',
                               '                released = not isinstance(dispose(resource), '
                               'BaseException)')],
 '모든 동기 예외: Exception만 흡수': [('except BaseException:', 'except Exception:')],
 '예외 흡수: 다시 전파': [('            except BaseException:\n                pass',
                   '            except BaseException:\n                raise')],
 '실패 뒤 계속: 첫 실패에서 중단': [('            except BaseException:\n                pass',
                         '            except BaseException:\n                break')],
 '실패 순서: 앞에 재보관': [('                    self._pending.append(resource)',
                    '                    self._pending.insert(0, resource)')],
 '실패 중복: 동일 객체 재보관 합치기': [('                    self._pending.append(resource)',
                           '                    if not any(item is resource for item in '
                           'self._pending):\n'
                           '                        self._pending.append(resource)')],
 '실패 객체 동일성: 마지막 객체로 대체': [('                    self._pending.append(resource)',
                            '                    self._pending.append(batch[-1])')],
 '횟수: 시도 수를 반환': [('            completed += released', '            completed += 1')],
 '반복 호출: 기존 실패 항목 버리기': [('        batch, self._pending = self._pending, []',
                          '        batch, self._pending = self._pending, []\n'
                          "        if getattr(self, '_swept', False):\n"
                          '            batch = []\n'
                          '        self._swept = True')],
 '반복 호출: 두 번째 재시도에서 버리기': [('        batch, self._pending = self._pending, []',
                            '        batch, self._pending = self._pending, []\n'
                            "        self._round = getattr(self, '_round', 0) + 1\n"
                            '        if self._round > 2:\n'
                            '            batch = []')],
 '실패 재시도: 보관만 하고 다음 sweep에서 생략': [('                dispose(resource)',
                                   '                if not any(item is resource for item in '
                                   "getattr(self, '_failed', [])):\n"
                                   '                    dispose(resource)'),
                                  ('                    self._pending.append(resource)',
                                   '                    self._pending.append(resource)\n'
                                   "                    self._failed = getattr(self, '_failed', "
                                   '[]) + [resource]')]}

SAFE = {'예외 절 표기': [('except BaseException:', 'except (Exception, BaseException):')],
 '성공 수 산술': [('completed += released', 'completed += int(released)')],
 '실패 분기 표기': [('if not released:', 'if released is False:')],
 '배치 복사': [('batch, self._pending = self._pending, []',
            'batch, self._pending = self._pending.copy(), []')],
 '순회 컨테이너': [('for resource in batch:', 'for resource in tuple(batch):')],
 '스냅샷 컨테이너': [('def pending(self) -> tuple[object, ...]:\n        return tuple(self._pending)',
               'def pending(self) -> list[object]:\n        return self._pending.copy()')],
 '예외 시 표지 재설정': [('            except BaseException:\n                pass',
                  '            except BaseException:\n                released = False')],
 '내부 저장 컨테이너': [('from collections.abc import Callable',
                 'from collections.abc import Callable\nfrom collections import deque'),
                ('self._pending: list[object] = []', 'self._pending: deque[object] = deque()'),
                ('batch, self._pending = self._pending, []',
                 'batch, self._pending = self._pending, deque()')],
 '성공 표지 숫자': [('released = False', 'released = 0'), ('released = True', 'released = 1')]}

RACY = {}

