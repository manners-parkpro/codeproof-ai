WEAKENED = {'초기화 원본을 그대로 공유': [('TRANSLATION = bytes(BOOTSTRAP)', 'TRANSLATION = BOOTSTRAP')],
 '원본을 읽기 전용 뷰로만 감쌈': [('TRANSLATION = bytes(BOOTSTRAP)',
                       'TRANSLATION = memoryview(BOOTSTRAP).toreadonly()')],
 '복사했지만 가변 바이트 배열': [('TRANSLATION = bytes(BOOTSTRAP)', 'TRANSLATION = bytearray(BOOTSTRAP)')],
 '읽기 전용 뷰의 obj는 가변 복사본': [('TRANSLATION = bytes(BOOTSTRAP)',
                           'TRANSLATION = memoryview(bytearray(BOOTSTRAP)).toreadonly()')],
 '반환 뷰만 초기화 원본을 노출': [('return memoryview(TRANSLATION)',
                       'return memoryview(BOOTSTRAP).toreadonly()')],
 '해제 가능한 뷰를 호출마다 재사용': [('TRANSLATION = bytes(BOOTSTRAP)',
                         'TRANSLATION = bytes(BOOTSTRAP)\nEXPORTED = memoryview(TRANSLATION)'),
                        ('return memoryview(TRANSLATION)', 'return EXPORTED')],
 '빈 입력에서만 크기 변경된 원본 사용': [('return data.translate(TRANSLATION)',
                           'return data.translate(BOOTSTRAP if not data else TRANSLATION)')],
 '단일 바이트 입력에서 가드 우회': [('return data.translate(TRANSLATION)',
                        'return data.translate(BOOTSTRAP if len(data) == 1 else TRANSLATION)')],
 '큰 입력에서 가드 우회': [('return data.translate(TRANSLATION)',
                   'return data.translate(BOOTSTRAP if len(data) > 1024 else TRANSLATION)')],
 'bytes 하위 타입에서 가드 우회': [('return data.translate(TRANSLATION)',
                          'return data.translate(BOOTSTRAP if type(data) is not bytes else '
                          'TRANSLATION)')]}

SAFE = {'버퍼 tobytes로 독립 불변 사본': [('TRANSLATION = bytes(BOOTSTRAP)',
                           'TRANSLATION = memoryview(BOOTSTRAP).tobytes()')],
 '초기화 원본을 먼저 복사': [('TRANSLATION = bytes(BOOTSTRAP)', 'TRANSLATION = bytes(BOOTSTRAP[:])')],
 '별도 불변 버퍼를 가진 반환 뷰': [('return memoryview(TRANSLATION)',
                        'return memoryview(bytes(bytearray(TRANSLATION)))')],
 '반환 뷰에 명시적 읽기 전용 지정': [('return memoryview(TRANSLATION)',
                         'return memoryview(TRANSLATION).toreadonly()')],
 '변환을 bytes 메서드로 직접 호출': [('return data.translate(TRANSLATION)',
                           'return bytes.translate(data, TRANSLATION)')],
 '일반 bytes 하위 타입으로 확정': [('TRANSLATION = bytes(BOOTSTRAP)',
                          'class FrozenBytes(bytes):\n'
                          '    pass\n'
                          '\n'
                          '\n'
                          'TRANSLATION = FrozenBytes(BOOTSTRAP)')]}

RACY = {}
