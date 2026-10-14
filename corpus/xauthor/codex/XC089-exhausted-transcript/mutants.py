WEAKENED = {'반복자 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
              '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
              '    pending = iter(messages)')],
 '원본 별도 순회로 pending 미소비': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                            '    paragraphs = [f"<p>{escape(text)}</p>" for text in messages]')],
 '지연 생성으로 소비 연기': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                    '    paragraphs = (f"<p>{escape(text)}</p>" for text in pending)'),
                   ('        paragraphs.append(_legacy_paragraph(text))',
                    '        return _legacy_paragraph(text)')],
 '목록 길이가 64 초과일 때만 접두사 소비': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                              '    paragraphs = [f"<p>{escape(text)}</p>" for text in '
                              '__import__("itertools").islice(pending, 64)]')],
 '첫 메시지만 남기는 역방향 복제': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                        '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                        '    if messages:\n'
                        '        pending = iter(messages[:1])')],
 '마지막 메시지만 잔여로 남김': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                      '    paragraphs = [f"<p>{escape(text)}</p>" for text in '
                      '__import__("itertools").islice(pending, max(0, len(messages) - 1))]')],
 '빈 목록에서만 잔여 분기': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                    '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                    '    if not messages:\n'
                    '        pending = iter([""])')],
 '빈 문자열에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                   '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                   '    if messages == [""]:\n'
                   '        pending = iter(messages)')],
 '목록 하위 타입에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                      '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                      '    if type(messages) is not list:\n'
                      '        pending = iter(messages)')],
 '문자열 하위 타입에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                       '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                       '    if any(type(text) is not str for text in messages):\n'
                       '        pending = iter(messages)')],
 'Enum 문자열에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                      '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                      '    if any(isinstance(text, __import__("enum").Enum) for text in '
                      'messages):\n'
                      '        pending = iter(messages)')],
 '장문에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                '    if any(len(text) > 65536 for text in messages):\n'
                '        pending = iter(messages)')],
 '제어문자에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                  '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                  '    if any("\\x00" in text for text in messages):\n'
                  '        pending = iter(messages)')],
 '서로게이트에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                   '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                   '    if any("\\ud800" in text for text in messages):\n'
                   '        pending = iter(messages)')],
 '두 번째 연속 호출에서만 재시작': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                        '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                        '    if getattr(render_transcript, "_previous", None) is messages:\n'
                        '        pending = iter(messages)\n'
                        '    render_transcript._previous = messages')],
 'assert 안에서만 소비': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                     '    paragraphs = []\n'
                     '    assert not [paragraphs.append(f"<p>{escape(text)}</p>") for text in '
                     'pending] or paragraphs')]}

SAFE = {'튜플 입력 스냅샷': [('pending = iter(messages)', 'pending = iter(tuple(messages))')],
 '목록 입력 스냅샷': [('pending = iter(messages)', 'pending = iter(messages.copy())')],
 'iter 재호출은 같은 반복자': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                       '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                       '    pending = iter(pending)')],
 '명시적 eager map': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                    '    paragraphs = list(map(lambda text: f"<p>{escape(text)}</p>", pending))')],
 '생성자를 tuple로 즉시 소비': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                        '    paragraphs = list(tuple(f"<p>{escape(text)}</p>" for text in '
                        'pending))')],
 '수동 루프로 끝까지 소비': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                    '    paragraphs = []\n'
                    '    for text in pending:\n'
                    '        paragraphs.append(f"<p>{escape(text)}</p>")')],
 '이스케이프 import 별칭': [('from html import escape', 'from html import escape as html_escape'),
                     ('escape(text)', 'html_escape(text)')],
 '모듈 import': [('from html import escape', 'import html'), ('escape(text)', 'html.escape(text)')],
 '동기 예외로 전체 거절': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                   '    raise ValueError("unsupported transcript")\n'
                   '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]')],
 '다른 동기 예외로 전체 거절': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                      '    raise RuntimeError("renderer unavailable")\n'
                      '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]')],
 '동기 예외 흡수 후 즉시 반환': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                       '    try:\n'
                       '        raise ValueError("unsupported transcript")\n'
                       '    except ValueError:\n'
                       '        return ""\n'
                       '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]')],
 '거꾸로 출력하되 전체 소비': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                     '    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]\n'
                     '    paragraphs.reverse()')],
 '출력 컨테이너 tuple': [('    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]',
                    '    paragraphs = tuple(f"<p>{escape(text)}</p>" for text in pending)')]}

RACY = {}
