WEAKENED: dict[str, list[tuple[str, str]]] = {'offset lower bound': [('if not 0 <= offset < size:', 'if not offset < size:')],
 'offset upper bound': [('if not 0 <= offset < size:', 'if not 0 <= offset:')],
 'offset inclusive upper bound': [('if not 0 <= offset < size:', 'if not 0 <= offset <= size:')],
 'value lower bound': [('if not 0 <= value <= 255:', 'if not value <= 255:')],
 'value upper bound': [('if not 0 <= value <= 255:', 'if not 0 <= value:')],
 'value inclusive 256': [('if not 0 <= value <= 255:', 'if not 0 <= value <= 256:')],
 'only validate first edit': [('for offset, value in edits:\n        if',
                               'for offset, value in edits[:1]:\n        if')],
 'only validate final edit': [('for offset, value in edits:\n        if',
                               'for offset, value in edits[-1:]:\n        if')],
 'skip middle edit': [('for offset, value in edits:\n        if',
                       'for offset, value in edits[:1] + edits[-1:]:\n        if')],
 'validate first sixteen edits': [('for offset, value in edits:\n        if',
                                   'for offset, value in edits[:16]:\n        if')],
 'validation after first write': [('    _validate_patch(len(buffer), edits)',
                                   '    if edits:\n'
                                   '        buffer[edits[0][0]] = edits[0][1]\n'
                                   '    _validate_patch(len(buffer), edits)')],
 'skip zero filled buffer': [('    _validate_patch(len(buffer), edits)',
                              '    if any(buffer):\n        _validate_patch(len(buffer), edits)')],
 'skip large buffer': [('    _validate_patch(len(buffer), edits)',
                        '    if len(buffer) < 256:\n        _validate_patch(len(buffer), edits)')],
 'skip offset subtypes': [('for offset, value in edits:\n        if',
                           'for offset, value in edits:\n'
                           '        if type(offset) is not int:\n'
                           '            continue\n'
                           '        if')],
 'skip value subtypes': [('for offset, value in edits:\n        if',
                          'for offset, value in edits:\n'
                          '        if type(value) is not int:\n'
                          '            continue\n'
                          '        if')],
 'skip extreme offsets': [('for offset, value in edits:\n        if',
                           'for offset, value in edits:\n'
                           '        if abs(offset) > 2**63:\n'
                           '            continue\n'
                           '        if')],
 'skip extreme values': [('for offset, value in edits:\n        if',
                          'for offset, value in edits:\n'
                          '        if abs(value) > 2**63:\n'
                          '            continue\n'
                          '        if')],
 'assert based validation': [('if not 0 <= offset < size:\n'
                              '            raise ValueError("offset outside buffer")',
                              'assert 0 <= offset < size, "offset outside buffer"'),
                             ('if not 0 <= value <= 255:\n'
                              '            raise ValueError("value outside byte range")',
                              'assert 0 <= value <= 255, "value outside byte range"')]}

SAFE: dict[str, list[tuple[str, str]]] = {'different rejection exception': [('raise ValueError("offset outside buffer")',
                                    'raise IndexError("bad position")'),
                                   ('raise ValueError("value outside byte range")',
                                    'raise OverflowError("bad byte")')],
 'validate tuple snapshot': [('for offset, value in edits:\n        if',
                              'for offset, value in tuple(edits):\n        if')],
 'reverse validation traversal': [('for offset, value in edits:\n        if',
                                   'for offset, value in reversed(edits):\n        if')],
 'range membership guard': [('if not 0 <= offset < size:', 'if offset not in range(size):'),
                            ('if not 0 <= value <= 255:', 'if value not in range(256):')],
 'check values before offsets': [('        if not 0 <= offset < size:\n'
                                  '            raise ValueError("offset outside buffer")\n'
                                  '        if not 0 <= value <= 255:\n'
                                  '            raise ValueError("value outside byte range")',
                                  '        if not 0 <= value <= 255:\n'
                                  '            raise ValueError("value outside byte range")\n'
                                  '        if not 0 <= offset < size:\n'
                                  '            raise ValueError("offset outside buffer")')],
 'empty buffer rejects at first assignment': [('    _validate_patch(len(buffer), edits)',
                                               '    if buffer:\n'
                                               '        _validate_patch(len(buffer), edits)')]}

RACY: dict[str, list[tuple[str, str]]] = {}
