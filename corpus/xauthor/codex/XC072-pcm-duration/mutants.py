"""주장의 입력 범위와 수치 경계 및 반환 계약에 대응하는 약화와 안전한 변형."""

WEAKENED = {'상한 포화 제거': [('min(max(seconds, 0.0), 0.5)', 'max(seconds, 0.0)')],
 '상한을 한 표본만 확장': [('min(max(seconds, 0.0), 0.5)', 'min(max(seconds, 0.0), 0.5001)')],
 '상한을 한 표본만 축소': [('min(max(seconds, 0.0), 0.5)', 'min(max(seconds, 0.0), 0.49999)')],
 '큰 유한 요청을 포화 대신 거절': [('    duration = min(max(seconds, 0.0), 0.5)',
                        '    if seconds > 0.5:\n'
                        "        raise ValueError('duration too long')\n"
                        '    duration = min(max(seconds, 0.0), 0.5)')],
 '하한 포화 제거': [('min(max(seconds, 0.0), 0.5)', 'min(seconds, 0.5)')],
 '음수 시간을 절댓값으로 환산': [('min(max(seconds, 0.0), 0.5)', 'min(abs(seconds), 0.5)')],
 '극단적 양수만 거절': [('    duration = min(max(seconds, 0.0), 0.5)',
                 '    if seconds > 1e300:\n'
                 "        raise ValueError('too large')\n"
                 '    duration = min(max(seconds, 0.0), 0.5)')],
 '극단적 음수만 잘못 포화': [('    duration = min(max(seconds, 0.0), 0.5)',
                    '    duration = 0.5 if seconds < -1e300 else min(max(seconds, 0.0), 0.5)')],
 '아주 작은 양수만 거절': [('    duration = min(max(seconds, 0.0), 0.5)',
                   '    if 0.0 < seconds < 1e-300:\n'
                   "        raise ValueError('too small')\n"
                   '    duration = min(max(seconds, 0.0), 0.5)')],
 '음의 영만 거절': [('    duration = min(max(seconds, 0.0), 0.5)',
               '    if seconds == 0.0 and math.copysign(1.0, seconds) < 0.0:\n'
               "        raise ValueError('negative zero')\n"
               '    duration = min(max(seconds, 0.0), 0.5)')],
 'NaN을 영으로 대체': [('    if not math.isfinite(seconds):',
                  '    if math.isnan(seconds):\n'
                  '        seconds = 0.0\n'
                  '    if not math.isfinite(seconds):')],
 '양의 무한대만 수용': [('    if not math.isfinite(seconds):',
                 '    if not math.isfinite(seconds) and seconds != math.inf:')],
 '음의 무한대만 수용': [('    if not math.isfinite(seconds):',
                 '    if not math.isfinite(seconds) and seconds != -math.inf:')],
 '평범한 하위 타입 거절': [('    if not math.isfinite(seconds):',
                   '    if type(seconds) is not float:\n'
                   "        raise TypeError('exact float required')\n"
                   '    if not math.isfinite(seconds):')],
 '문자열 경유가 Enum 혼합형을 거절': [('    if not math.isfinite(seconds):',
                           '    seconds = float(str(seconds))\n'
                           '    if not math.isfinite(seconds):')],
 '부분 표본을 올림': [('int(duration * 16000)', 'math.ceil(duration * 16000)')],
 '부분 표본을 반올림': [('int(duration * 16000)', 'round(duration * 16000)')],
 '영 길이를 한 표본으로 변경': [('int(duration * 16000)', 'max(1, int(duration * 16000))')],
 '표본 폭을 한 바이트로 변경': [('bytearray(samples * 2)', 'bytearray(samples)')],
 '비영 바이트로 초기화': [('bytearray(samples * 2)', "bytearray(b'\\x01' * (samples * 2))")],
 '불변 반환 컨테이너': [('bytearray(samples * 2)', 'bytes(samples * 2)')],
 '버퍼 캐시로 호출자 변경 전파': [('import math', 'import math\nfrom functools import cache'),
                      ('def _pcm_buffer(samples: int) -> bytearray:',
                       '@cache\ndef _pcm_buffer(samples: int) -> bytearray:')],
 '공유 버퍼를 다시 영으로 채움': [('import math', 'import math\n\n_buffer = bytearray()'),
                      ('    return bytearray(samples * 2)',
                       "    _buffer[:] = b'\\x00' * (samples * 2)\n    return _buffer")],
 '거절 이력이 다음 성공을 오염': [('        raise ValueError("duration must be finite")',
                       '        global _failed\n'
                       '        _failed = True\n'
                       '        raise ValueError("duration must be finite")'),
                      ('    return _pcm_buffer(samples)',
                       "    if globals().get('_failed', False):\n"
                       '        return bytearray()\n'
                       '    return _pcm_buffer(samples)')]}

SAFE = {'거절 예외 타입 변경': [('raise ValueError("duration must be finite")',
                  'raise ArithmeticError("duration must be finite")')],
 '내림 후 표본 수가 같은 상한 여유': [('min(max(seconds, 0.0), 0.5)',
                              'min(max(seconds, 0.0), 0.5000625)')],
 '분기식으로 같은 포화': [('min(max(seconds, 0.0), 0.5)',
                  '0.0 if seconds < 0.0 else 0.5 if seconds > 0.5 else seconds')],
 '표본 단위로 포화 이동': [('    duration = min(max(seconds, 0.0), 0.5)\n'
                   '    samples = int(duration * 16000)',
                   '    samples = int(min(max(seconds * 16000, 0.0), 8000.0))')],
 'float 하위 타입을 값으로 정규화': [('    if not math.isfinite(seconds):',
                           '    seconds = float(seconds)\n    if not math.isfinite(seconds):')],
 'floor로 비음수 정수 변환': [('int(duration * 16000)', 'math.floor(duration * 16000)')],
 '별도 이름으로 표준 라이브러리 import': [('import math', 'import math as numeric'),
                             ('math.isfinite(seconds)', 'numeric.isfinite(seconds)')],
 '명시적인 영 바이트 초기화': [('bytearray(samples * 2)', "bytearray(b'\\x00' * (samples * 2))")],
 'bytearray의 평범한 하위 타입 반환': [('import math', 'import math\n\n\nclass PCM(bytearray):\n    pass'),
                             ('bytearray(samples * 2)', 'PCM(samples * 2)')]}

RACY = {}
