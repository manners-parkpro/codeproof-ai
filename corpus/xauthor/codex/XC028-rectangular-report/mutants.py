"""주장의 입력 축별 약화와 예외, 컨테이너, 검증식의 안전한 변형."""

WEAKENED = {'shorter-row-accepted': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                           'if rows and any(len(row) > len(rows[0]) for row in rows):')],
 'longer-row-accepted': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                          'if rows and any(len(row) < len(rows[0]) for row in rows):')],
 'only-first-two-rows': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                          'if rows and any(len(row) != len(rows[0]) for row in rows[:2]):')],
 'last-row-unchecked': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                         'if rows and any(len(row) != len(rows[0]) for row in rows[:-1]):')],
 'empty-later-row-skipped': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                              'if rows and any(len(row) != len(rows[0]) for row in rows if row):')],
 'empty-first-row-skips-check': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                                  'if rows and rows[0] and any(len(row) != len(rows[0]) for row in '
                                  'rows):')],
 'one-cell-tolerance': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                         'if rows and any(abs(len(row) - len(rows[0])) > 1 for row in rows):')],
 'bounded-row-scan': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                       'if rows and any(len(row) != len(rows[0]) for row in rows[:64]):')],
 'bounded-width-scan': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                         'if rows and any(len(row[:256]) != len(rows[0][:256]) for row in rows):')],
 'exact-tuples-only': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                        'if type(rows) is tuple and rows and any(len(row) != len(rows[0]) for row '
                        'in rows):')],
 'exact-inner-tuples-only': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                              'if rows and any(len(row) != len(rows[0]) for row in rows if '
                              'type(row) is tuple):')],
 'assert-guard': [('raise ValueError("inconsistent report width")',
                   'assert False, "inconsistent report width"')],
 'empty-input-rejected': [('    _validate_widths(rows)',
                           '    if not rows:\n'
                           '        raise ValueError("empty report")\n'
                           '    _validate_widths(rows)')],
 'zero-width-rejected': [('    _validate_widths(rows)',
                          '    if rows and not rows[0]:\n'
                          '        raise ValueError("empty row")\n'
                          '    _validate_widths(rows)')],
 'ragged-none-sentinel': [('    _validate_widths(rows)',
                           '    if len({len(row) for row in rows}) > 1:\n'
                           '        return None\n'
                           '    _validate_widths(rows)')],
 'row-order-reversed': [('return tuple(zip(*rows))', 'return tuple(zip(*reversed(rows)))')],
 'column-order-reversed': [('return tuple(zip(*rows))',
                            'return tuple(reversed(tuple(zip(*rows))))')],
 'duplicate-columns-collapsed': [('return tuple(zip(*rows))',
                                  'return tuple(dict.fromkeys(zip(*rows)))')],
 'cells-stringified': [('return tuple(zip(*rows))',
                        'return tuple(tuple(str(cell) for cell in column) for column in '
                        'zip(*rows))')],
 'empty-cells-filtered': [('return tuple(zip(*rows))',
                           'return tuple(tuple(cell for cell in column if cell) for column in '
                           'zip(*rows))')],
 'cell-content-stripped': [('return tuple(zip(*rows))',
                            'return tuple(tuple(cell.strip() for cell in column) for column in '
                            'zip(*rows))')]}

SAFE = {'exception-type': [('raise ValueError("inconsistent report width")',
                     'raise RuntimeError("inconsistent report width")')],
 'all-equal-validator': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                          'if rows and not all(len(row) == len(rows[0]) for row in rows):')],
 'distinct-width-validator': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                               'if len({len(row) for row in rows}) > 1:')],
 'strict-zip': [('return tuple(zip(*rows))', 'return tuple(zip(*rows, strict=True))')],
 'list-container': [(') -> tuple[tuple[str, ...], ...]:', ') -> list[tuple[str, ...]]:'),
                    ('return tuple(zip(*rows))', 'return list(zip(*rows))')],
 'qualified-import': [('from __future__ import annotations',
                       'from __future__ import annotations\n\nimport builtins'),
                      ('return tuple(zip(*rows))', 'return tuple(builtins.zip(*rows))')],
 'last-row-reference': [('if rows and any(len(row) != len(rows[0]) for row in rows):',
                         'if rows and any(len(row) != len(rows[-1]) for row in rows):')]}

RACY = {}
