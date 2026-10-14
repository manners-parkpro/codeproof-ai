"""주장 축별 약화와 안전한 파서, 예외 및 import 변형."""

WEAKENED = {'object hook creates legacy object': [('    return json.loads(document)',
                                        '    return json.loads(document, object_hook=lambda obj: '
                                        '_ShellPreview(**obj))')],
 'empty object fallback': [('    return json.loads(document)',
                            '    step = json.loads(document)\n'
                            '    if step == {}:\n'
                            '        return _ShellPreview("printf XC070_PROBE")\n'
                            '    return step')],
 'array command becomes legacy object': [('    return json.loads(document)',
                                          '    step = json.loads(document)\n'
                                          '    if isinstance(step, list) and len(step) == 1 and '
                                          'isinstance(step[0], str):\n'
                                          '        return _ShellPreview(step[0])\n'
                                          '    return step')],
 'string command becomes legacy object': [('    return json.loads(document)',
                                           '    step = json.loads(document)\n'
                                           '    if isinstance(step, str) and bool(step):\n'
                                           '        return _ShellPreview(step)\n'
                                           '    return step')],
 'empty string fallback': [('    return json.loads(document)',
                            '    step = json.loads(document)\n'
                            "    if step == '':\n"
                            '        return _ShellPreview("printf XC070_PROBE")\n'
                            '    return step')],
 'null fallback': [('    return json.loads(document)',
                    '    step = json.loads(document)\n'
                    '    if step is None:\n'
                    '        return _ShellPreview("printf XC070_PROBE")\n'
                    '    return step')],
 'boolean fallback': [('    return json.loads(document)',
                       '    step = json.loads(document)\n'
                       '    if type(step) is bool:\n'
                       '        return _ShellPreview("printf XC070_PROBE")\n'
                       '    return step')],
 'large negative integer fallback': [('    return json.loads(document)',
                                      '    step = json.loads(document)\n'
                                      '    if type(step) is int and step < -(2**128):\n'
                                      '        return _ShellPreview("printf XC070_PROBE")\n'
                                      '    return step')],
 'large positive integer fallback': [('    return json.loads(document)',
                                      '    step = json.loads(document)\n'
                                      '    if type(step) is int and step > 2**128:\n'
                                      '        return _ShellPreview("printf XC070_PROBE")\n'
                                      '    return step')],
 'fractional number fallback': [('    return json.loads(document)',
                                 '    step = json.loads(document)\n'
                                 '    if type(step) is float and 0 < step < 1:\n'
                                 '        return _ShellPreview("printf XC070_PROBE")\n'
                                 '    return step')],
 'negative zero fallback': [('    return json.loads(document)',
                             '    step = json.loads(document)\n'
                             '    if type(step) is float and step == 0 and '
                             "str(step).startswith('-'):\n"
                             '        return _ShellPreview("printf XC070_PROBE")\n'
                             '    return step')],
 'nan fallback': [('    return json.loads(document)',
                   '    step = json.loads(document)\n'
                   '    if type(step) is float and step != step:\n'
                   '        return _ShellPreview("printf XC070_PROBE")\n'
                   '    return step')],
 'infinite fallback': [('    return json.loads(document)',
                        '    step = json.loads(document)\n'
                        "    if step == float('inf') or step == float('-inf'):\n"
                        '        return _ShellPreview("printf XC070_PROBE")\n'
                        '    return step')],
 'nested object legacy promotion': [('    return json.loads(document)',
                                     '    step = json.loads(document)\n'
                                     '    if isinstance(step, dict) and '
                                     "isinstance(step.get('outer'), dict):\n"
                                     "        return _ShellPreview(step['outer']['command'])\n"
                                     '    return step')],
 'nested array legacy promotion': [('    return json.loads(document)',
                                    '    step = json.loads(document)\n'
                                    '    while isinstance(step, list) and len(step) == 1:\n'
                                    '        step = step[0]\n'
                                    "    if isinstance(step, dict) and 'command' in step:\n"
                                    "        return _ShellPreview(step['command'])\n"
                                    '    return step')],
 'empty document fallback': [('    return json.loads(document)',
                              "    if document == '':\n"
                              "        return _ShellPreview('printf XC070_PROBE')\n"
                              '    return json.loads(document)')],
 'invalid nonempty JSON fallback': [('    return json.loads(document)',
                                     '    try:\n'
                                     '        return json.loads(document)\n'
                                     '    except ValueError:\n'
                                     '        if document:\n'
                                     '            return _ShellPreview(document)\n'
                                     '        raise')],
 'large document legacy promotion': [('    return json.loads(document)',
                                      '    if len(document) > 10000:\n'
                                      "        return _ShellPreview('printf XC070_PROBE')\n"
                                      '    return json.loads(document)')],
 'plain str subclass fallback': [('    return json.loads(document)',
                                  '    if type(document) is not str and not hasattr(document, '
                                  "'value'):\n"
                                  "        return _ShellPreview('printf XC070_PROBE')\n"
                                  '    return json.loads(document)')],
 'string enum fallback': [('    return json.loads(document)',
                           "    if isinstance(document, str) and hasattr(document, 'value'):\n"
                           "        return _ShellPreview('printf XC070_PROBE')\n"
                           '    return json.loads(document)')],
 'escaped command name hook': [('    return json.loads(document)',
                                "    if '\\\\u0063ommand' in document:\n"
                                '        return json.loads(document, object_hook=lambda obj: '
                                '_ShellPreview(**obj))\n'
                                '    return json.loads(document)')],
 'whitespace prefix legacy fallback': [('    return json.loads(document)',
                                        "    if document.startswith('\\t{'):\n"
                                        "        return _ShellPreview('printf XC070_PROBE')\n"
                                        '    return json.loads(document)')],
 'deep document legacy promotion': [('    return json.loads(document)',
                                     "    if document.startswith('[' * 64):\n"
                                     "        return _ShellPreview('printf XC070_PROBE')\n"
                                     '    return json.loads(document)')]}

SAFE = {'default JSONDecoder': [('    return json.loads(document)',
                          '    return json.JSONDecoder().decode(document)')],
 'module import alias': [('import json', 'import json as codec'),
                         ('json.loads(document)', 'codec.loads(document)'),
                         ('json.dumps(step, ensure_ascii=True, sort_keys=True)',
                          'codec.dumps(step, ensure_ascii=True, sort_keys=True)')],
 'function import alias': [('import json', 'import json\nfrom json import loads as parse_document'),
                           ('json.loads(document)', 'parse_document(document)')],
 'direct sink import': [('import subprocess', 'from subprocess import check_output'),
                        ('subprocess.check_output(step.command, shell=True, text=True)',
                         'check_output(step.command, shell=True, text=True)')],
 'equivalent dict object hook': [('    return json.loads(document)',
                                  '    return json.loads(document, object_hook=dict)')],
 'equivalent pairs hook': [('    return json.loads(document)',
                            '    return json.loads(document, object_pairs_hook=dict)')],
 'changed rejection type': [('    return json.loads(document)',
                             '    try:\n'
                             '        return json.loads(document)\n'
                             '    except ValueError as exc:\n'
                             "        raise RuntimeError('invalid document') from exc")],
 'unescaped preview output': [('ensure_ascii=True, sort_keys=True',
                               'ensure_ascii=False, sort_keys=False')],
 'exact legacy type dispatch': [('isinstance(step, _ShellPreview)', 'type(step) is _ShellPreview')]}

RACY = {}
