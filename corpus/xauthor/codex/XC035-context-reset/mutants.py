"""주장의 각 절을 겨냥한 변이 - 객체 보존과 종료 순서 및 복원을 구별한다."""

WEAKENED = {'콜백 실패 때 복원 누락': [('        finally:\n            _request_id.reset(token)',
                    '        else:\n            _request_id.reset(token)')],
 '이전 바인딩 대신 초기값 복원': [('            _request_id.reset(token)',
                       '            _request_id.set(None)')],
 '바인딩 전체 미복원': [('            _request_id.reset(token)', '            pass')],
 '종료 전에 이전 바인딩 노출': [('            finish()\n'
                      '        except BaseException:\n'
                      '            pass\n'
                      '        finally:\n'
                      '            _request_id.reset(token)',
                      '            _request_id.reset(token)\n'
                      '            finish()\n'
                      '        except BaseException:\n'
                      '            pass')],
 '본문 진입 바인딩 누락': [('    token = _request_id.set(request_id)',
                   '    token = _request_id.set(_request_id.get())')],
 'as 객체 대체': [('        yield request_id', '        yield None')],
 '하위 타입 객체 문자열로 재생성': [('    token = _request_id.set(request_id)',
                        '    token = _request_id.set(str(request_id))')],
 '빈 식별자 이전 값으로 대체': [('    token = _request_id.set(request_id)',
                      '    token = _request_id.set(request_id or _request_id.get())')],
 '긴 식별자 잘라 저장': [('    token = _request_id.set(request_id)',
                  '    token = _request_id.set(request_id if len(request_id) < 65536 else '
                  'request_id[:65535])')],
 '종료 콜백 누락': [('            finish()', '            pass')],
 '정상 종료 콜백 중복': [('            finish()', '            finish()\n            finish()')],
 '콜백 Exception만 흡수': [('        except BaseException:', '        except Exception:')],
 '콜백 StopIteration만 재전파': [('        except BaseException:',
                            '        except StopIteration:\n'
                            '            raise\n'
                            '        except BaseException:')],
 '콜백 오류를 전파': [('        except BaseException:\n            pass',
                '        except BaseException:\n            raise')],
 '본문 예외를 흡수': [('        yield request_id\n    finally:',
                '        yield request_id\n    except BaseException:\n        pass\n    finally:')],
 '본문 예외 객체를 복제': [('        yield request_id\n    finally:',
                   '        yield request_id\n'
                   '    except BaseException as exc:\n'
                   '        raise type(exc)(*exc.args)\n'
                   '    finally:')],
 '본문 실패시에만 종료 콜백': [('            finish()',
                     '            import sys\n'
                     '            if sys.exc_info()[0] is not None:\n'
                     '                finish()')],
 '본문 성공시에만 종료 콜백': [('            finish()',
                     '            import sys\n'
                     '            if sys.exc_info()[0] is None:\n'
                     '                finish()')],
 '깊은 중첩에서 이전 바인딩 무시': [('            _request_id.reset(token)',
                        '            _request_id.reset(token)\n'
                        "            if _request_id.get() == '14':\n"
                        '                _request_id.set(None)')],
 '정리 콜백의 중첩만 복원 누락': [('            _request_id.reset(token)',
                       "            if request_id != 'finish-child':\n"
                       '                _request_id.reset(token)')]}

SAFE = {'예외 별칭은 무관': [('        except BaseException:', '        except BaseException as ignored:')],
 '흡수 직후 순차 복원': [('        finally:\n            _request_id.reset(token)',
                  '        _request_id.reset(token)')],
 '동일 객체 지역 이름': [('        yield request_id', '        bound = request_id\n        yield bound')],
 'ContextVar의 진단용 이름 변경': [('ContextVar("request_id", default=None)',
                            'ContextVar("scoped_request", default=None)')],
 '초기 기본값을 get에서 제공': [('ContextVar("request_id", default=None)', 'ContextVar("request_id")'),
                      ('    return _request_id.get()', '    return _request_id.get(None)')],
 '표준 suppress로 종료 예외 흡수': [('from contextlib import contextmanager',
                            'from contextlib import contextmanager, suppress'),
                           ('        try:\n'
                            '            finish()\n'
                            '        except BaseException:\n'
                            '            pass\n'
                            '        finally:\n'
                            '            _request_id.reset(token)',
                            '        try:\n'
                            '            with suppress(BaseException):\n'
                            '                finish()\n'
                            '        finally:\n'
                            '            _request_id.reset(token)')],
 '제네릭 별칭 import': [('from contextvars import ContextVar',
                    'from contextvars import ContextVar as RequestVariable'),
                   ('_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)',
                    '_request_id: RequestVariable[str | None] = RequestVariable("request_id", '
                    'default=None)')]}

RACY = {}
