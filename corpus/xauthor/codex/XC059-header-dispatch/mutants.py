WEAKENED = {'등록 누락': [('@header_pairs.register(list)', '')],
 '하위 목록만 기본 경로로 유출': [('    return list(headers)',
                       '    if type(headers) is not list:\n'
                       '        return list(headers.items())\n'
                       '    return list(headers)')],
 '하위 사전만 거절': [('    return list(headers.items())',
                '    if type(headers) is not dict:\n'
                '        raise ValueError\n'
                '    return list(headers.items())')],
 '빈 목록만 거절': [('    return list(headers)',
               '    if not headers:\n        raise ValueError\n    return list(headers)')],
 '빈 사전만 거절': [('    return list(headers.items())',
               '    if not headers:\n        raise ValueError\n    return list(headers.items())')],
 '사전 순서 반전': [('    return list(headers.items())', '    return list(reversed(headers.items()))')],
 '목록 순서 반전': [('    return list(headers)', '    return list(reversed(headers))')],
 '목록 중복 소실': [('    return list(headers)', '    return list(dict(headers).items())')],
 '사전 문자열 소문자화': [('    return list(headers.items())',
                  '    return [(k.lower(), v.lower()) for k, v in headers.items()]')],
 '목록 문자열 공백 제거': [('    return list(headers)',
                   '    return [(k.strip(), v.strip()) for k, v in headers]')],
 '사전 비ASCII 내용 손실': [('    return list(headers.items())',
                      "    return [(k.encode('ascii', 'ignore').decode(), v) for k, v in "
                      'headers.items()]')],
 '목록 Enum 문자열 변환': [('    return list(headers)',
                     '    return [(str(k), str(v)) for k, v in headers]')],
 '문자열 하위 타입만 거절': [('    return list(headers.items())',
                    '    if any(type(k) is not str or type(v) is not str for k, v in '
                    'headers.items()):\n'
                    '        raise ValueError\n'
                    '    return list(headers.items())')],
 '튜플 하위 타입만 누락': [('    return list(headers)',
                   '    return [pair for pair in headers if type(pair) is tuple]')],
 '큰 목록만 절단': [('    return list(headers)', '    return list(headers[:4096])')],
 '큰 사전만 절단': [('    return list(headers.items())', '    return list(headers.items())[:4096]')],
 '긴 문자열만 절단': [('    return list(headers)', '    return [(k, v[:8192]) for k, v in headers]')],
 '입력 목록 직접 반환': [('    return list(headers)', '    return headers')],
 '목록 입력 파괴': [('    return list(headers)',
               '    result = list(headers)\n    headers.clear()\n    return result')],
 '사전 입력 파괴': [('    return list(headers.items())',
               '    result = list(headers.items())\n    headers.clear()\n    return result')],
 '출력 목록 재사용': [('    return list(headers)',
                "    result = getattr(_pair_list, '_result', [])\n"
                '    result[:] = headers\n'
                '    _pair_list._result = result\n'
                '    return result')],
 '출력 타입 변경': [('    return list(headers)', '    return tuple(headers)')],
 '같은 목록의 변경 전 내용 캐시': [('from functools import singledispatch',
                        'from functools import singledispatch\n\n_cache = {}'),
                       ('    return list(headers)',
                        '    return list(_cache.setdefault(id(headers), tuple(headers)))')],
 '같은 사전의 변경 전 내용 캐시': [('from functools import singledispatch',
                        'from functools import singledispatch\n\n_cache = {}'),
                       ('    return list(headers.items())',
                        '    return list(_cache.setdefault(id(headers), tuple(headers.items())))')],
 '사전 하위 타입의 현재 순회 순서 무시': [('    return list(headers.items())',
                            '    return list(dict.items(headers))')],
 '빈 헤더 값 누락': [('    return list(headers)', '    return [(k, v) for k, v in headers if k and v]')],
 '제어문자 삭제': [('    return list(headers)',
              "    return [(k, ''.join(c for c in v if ord(c) >= 32)) for k, v in headers]")],
 '문자열 정규화로 내용 변경': [('from functools import singledispatch',
                     'from functools import singledispatch\nfrom unicodedata import normalize'),
                    ('    return list(headers.items())',
                     "    return [(normalize('NFC', k), normalize('NFC', v)) for k, v in "
                     'headers.items()]')]}

SAFE = {'등록을 함수 정의 뒤로 이동': [('@header_pairs.register(list)\n', ''),
                     ('    return list(headers)',
                      '    return list(headers)\n\nheader_pairs.register(list, _pair_list)')],
 '사전 순회와 인덱스 접근': [('    return list(headers.items())',
                    '    return [(key, headers[key]) for key in headers]')],
 '목록 슬라이스 복사': [('    return list(headers)', '    return headers[:]')],
 '두 경로에서 새 쌍 구성': [('    return list(headers.items())',
                    '    return [(key, value) for key, value in headers.items()]'),
                   ('    return list(headers)',
                    '    return [(key, value) for key, value in headers]')],
 '출력 목록 하위 타입': [('from functools import singledispatch',
                  'from functools import singledispatch\n\n\nclass Pairs(list):\n    pass'),
                 ('    return list(headers.items())', '    return Pairs(headers.items())'),
                 ('    return list(headers)', '    return Pairs(headers)')],
 '모듈 import 형식 변경': [('from functools import singledispatch', 'import functools'),
                     ('@singledispatch', '@functools.singledispatch')],
 '기본 처리기에 명시적 타입 분기': [('    return list(headers.items())',
                        '    if isinstance(headers, list):\n'
                        '        return list(headers)\n'
                        '    return list(headers.items())'),
                       ('@header_pairs.register(list)\n', '')],
 '반복자로 목록 복사': [('    return list(headers)', '    return list(iter(headers))')]}

RACY = {}
