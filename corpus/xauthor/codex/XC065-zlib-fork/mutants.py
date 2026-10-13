WEAKENED = {'복사 우회': [('return source.copy()', 'return source')],
 '빈 입력에서만 복사 생략': [('staged = fork_stream(source)',
                    'staged = fork_stream(source) if payload else source')],
 '거절 뒤 원본 진행': [('        raise ValueError("chunk exceeds limit")',
                 '        source.compress(payload)\n'
                 '        source.flush(zlib.Z_SYNC_FLUSH)\n'
                 '        raise ValueError("chunk exceeds limit")')],
 '복사 대신 새 압축기로 이력과 설정 소실': [('return source.copy()', 'return zlib.compressobj()')],
 '복사 전에 원본 압축': [('    staged = fork_stream(source)',
                  '    source.compress(payload)\n    staged = fork_stream(source)')],
 '빈 입력 부당 거절': [('    staged = fork_stream(source)',
                 '    if not payload:\n'
                 '        raise ValueError("empty")\n'
                 '    staged = fork_stream(source)')],
 'bytes 하위 타입 부당 거절': [('    staged = fork_stream(source)',
                        '    if type(payload) is not bytes:\n'
                        '        raise ValueError("subclass")\n'
                        '    staged = fork_stream(source)')],
 '일반 int 하위 타입 부당 거절': [('    staged = fork_stream(source)',
                         '    if type(limit) not in (int, bool) and not hasattr(limit, "name"):\n'
                         '        raise ValueError("subclass")\n'
                         '    staged = fork_stream(source)')],
 '정확한 크기 경계 거절': [('if len(block) > limit:', 'if len(block) >= limit:')],
 '음수 상한 우회': [('if len(block) > limit:', 'if limit >= 0 and len(block) > limit:')],
 '상한을 기계 정수로 제한': [('    staged = fork_stream(source)',
                    '    limit.to_bytes(8, "big", signed=True)\n    staged = fork_stream(source)')],
 '긴 입력 뒷부분 유실': [('    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)',
                  '    block = staged.compress(payload[:65536]) + '
                  'staged.flush(zlib.Z_SYNC_FLUSH)')],
 'flush 출력 누락': [('    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)',
                  '    block = staged.compress(payload)\n    staged.flush(zlib.Z_SYNC_FLUSH)')],
 '입력 전 flush로 순서 변경': [('    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)',
                        '    block = staged.flush(zlib.Z_SYNC_FLUSH) + staged.compress(payload)')],
 'FULL_FLUSH로 후속 압축 이력 소실': [('    block = staged.compress(payload) + '
                              'staged.flush(zlib.Z_SYNC_FLUSH)',
                              '    block = staged.compress(payload) + '
                              'staged.flush(zlib.Z_FULL_FLUSH)')],
 '미리 보기에서 스트림 종료': [('    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)',
                     '    block = staged.compress(payload) + staged.flush(zlib.Z_FINISH)')],
 '반환 상태를 압축 이전으로 되돌림': [('return block, staged', 'return block, source.copy()')],
 '반환 압축기만 원본으로 바꿈': [('return block, staged', 'return block, source')],
 '종료된 원본을 새 압축기로 대체': [('    return source.copy()',
                        '    try:\n'
                        '        return source.copy()\n'
                        '    except (ValueError, zlib.error):\n'
                        '        return zlib.compressobj()')],
 'bool 상한 검사 우회': [('if len(block) > limit:',
                    'if not isinstance(limit, bool) and len(block) > limit:')],
 'IntEnum 상한 검사 우회': [('if len(block) > limit:',
                       'if not hasattr(limit, "name") and len(block) > limit:')],
 '빈 청크의 동일한 후속 상태를 근거로 원본 반환': [('return block, staged',
                                 'return block, source if not payload and len(block) == 5 else '
                                 'staged')]}

SAFE = {'거절 예외 종류 변경': [('raise ValueError("chunk exceeds limit")',
                  'raise OverflowError("chunk exceeds limit")')],
 '출력 조립 컨테이너 변경': [('    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)',
                    '    pieces = [staged.compress(payload), staged.flush(zlib.Z_SYNC_FLUSH)]\n'
                    '    block = b"".join(pieces)')],
 '반환 압축기를 한 번 더 복사': [('return block, staged', 'return block, staged.copy()')],
 '복사를 호출부로 이동': [('    return source.copy()', '    return source'),
                 ('staged = fork_stream(source)', 'staged = fork_stream(source.copy())')],
 '비교 방향 변경': [('if len(block) > limit:', 'if limit < len(block):')],
 '표준 라이브러리 import 별칭': [('import zlib', 'import zlib as codec'),
                        ('Compressor = type(zlib.compressobj())',
                         'Compressor = type(codec.compressobj())'),
                        ('    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)',
                         '    block = staged.compress(payload) + '
                         'staged.flush(codec.Z_SYNC_FLUSH)')]}

RACY = {}
