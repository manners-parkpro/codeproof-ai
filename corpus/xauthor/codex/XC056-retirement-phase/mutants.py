WEAKENED = {'생성 실패 흡수': [('            if not installed:\n                raise', '            pass')],
 '시작부터 교체 완료': [('        installed = False', '        installed = True')],
 '생성 두 번': [('            replacement = factory()',
             '            factory()\n            replacement = factory()')],
 '생성 생략': [('            replacement = factory()', '            replacement = self._value')],
 '생성 전 기존 값 폐기': [('            replacement = factory()',
                   '            self._value = None\n            replacement = factory()')],
 '생성 예외 객체 재구성': [('        except BaseException:\n'
                   '            if not installed:\n'
                   '                raise',
                   '        except BaseException as exc:\n'
                   '            if not installed:\n'
                   '                raise type(exc)(*exc.args)')],
 '종료 계열 정리 실패 누출': [('        except BaseException:', '        except Exception:')],
 '정리 성공에만 완료 표시': [('            installed = True\n'
                    '            if previous is not replacement:\n'
                    '                retire(previous)',
                    '            if previous is not replacement:\n'
                    '                retire(previous)\n'
                    '            installed = True')],
 '정리 뒤 게시': [('            self._value = replacement\n'
              '            installed = True\n'
              '            if previous is not replacement:\n'
              '                retire(previous)',
              '            installed = True\n'
              '            if previous is not replacement:\n'
              '                retire(previous)\n'
              '            self._value = replacement')],
 '이전 객체 대신 새 객체 정리': [('                retire(previous)',
                       '                retire(replacement)')],
 '정리 중복 호출': [('                retire(previous)',
               '                retire(previous)\n                retire(previous)')],
 '같은 객체도 정리': [('            if previous is not replacement:', '            if True:')],
 '동등한 별개 객체 정리 생략': [('            if previous is not replacement:',
                      '            if previous != replacement:')],
 '빈 기존 값 정리 생략': [('            if previous is not replacement:',
                   '            if previous and previous is not replacement:')],
 'None 기존 값 정리 생략': [('            if previous is not replacement:',
                      '            if previous is not None and previous is not replacement:')],
 '빈 새 값 정리 생략': [('            if previous is not replacement:',
                  '            if replacement and previous is not replacement:')],
 '정리 반환값을 슬롯에 게시': [('                retire(previous)',
                     '                self._value = retire(previous)')],
 '교체 결과를 이전 값으로 반환': [('                raise\n        return self._value',
                       '                raise\n        return previous')],
 'current의 빈 값 대체': [('    def current(self) -> object:\n        return self._value',
                      '    def current(self) -> object:\n'
                      '        return self._value or object()')],
 '두 번째 성공 교체 생략': [('        installed = False',
                    "        if getattr(self, '_replaced', False):\n"
                    '            return self._value\n'
                    '        installed = False'),
                   ('            self._value = replacement',
                    '            self._value = replacement\n'
                    '            self._replaced = True')],
 '반환값 복사로 동일성 손실': [('                raise\n        return self._value',
                     '                raise\n'
                     '        from copy import copy\n'
                     '        return copy(self._value)')],
 '주장 대신 assert로 생성 실패 처리': [('            if not installed:\n                raise',
                             '            if not installed:\n'
                             '                assert installed')]}

SAFE = {'typing의 Callable': [('from collections.abc import Callable', 'from typing import Callable')],
 '정수 완료 플래그': [('        installed = False', '        installed = 0'),
               ('            installed = True', '            installed = 1')],
 '정리 결과 무시를 명시': [('                retire(previous)',
                   '                ignored_result = retire(previous)')],
 '예외 이름 바인딩': [('        except BaseException:',
                '        except BaseException as cleanup_error:')],
 '같은 객체는 조기 반환': [('            if previous is not replacement:\n'
                   '                retire(previous)',
                   '            if previous is replacement:\n'
                   '                return replacement\n'
                   '            retire(previous)')],
 '슬롯 값은 단일 원소 리스트에 보관': [('        self._value = value', '        self._value = [value]'),
                         ('    def current(self) -> object:\n        return self._value',
                          '    def current(self) -> object:\n        return self._value[0]'),
                         ('            previous = self._value\n'
                          '            self._value = replacement',
                          '            previous = self._value[0]\n'
                          '            self._value[0] = replacement'),
                         ('                raise\n        return self._value',
                          '                raise\n        return self._value[0]')],
 '생성 호출을 예외 흡수 범위 밖으로 이동': [('        installed = False\n'
                             '        try:\n'
                             '            replacement = factory()',
                             '        replacement = factory()\n'
                             '        installed = False\n'
                             '        try:')],
 '정리 실패 뒤 새 값 직접 반환': [('                raise\n        return self._value',
                        '                raise\n        return replacement')]}

RACY = {}
