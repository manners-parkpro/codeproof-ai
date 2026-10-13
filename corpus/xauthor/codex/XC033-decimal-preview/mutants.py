WEAKENED = {'copy_bypassed': [('working = template.copy()', 'working = template')],
 'copy_skipped_when_precision_matches': [('working = template.copy()',
                                          'working = template.copy() if precision != template.prec '
                                          'else template')],
 'copy_skipped_for_clean_flags': [('working = template.copy()',
                                   'working = template.copy() if any(template.flags.values()) else '
                                   'template')],
 'copy_skipped_for_disabled_traps': [('working = template.copy()',
                                      'working = template.copy() if any(template.traps.values()) '
                                      'else template')],
 'plain_subclass_not_copied': [('working = template.copy()',
                                'working = template.copy() if type(template) is Context else '
                                'template')],
 'nan_fast_path_bypasses_copy': [('working = template.copy()',
                                  'working = template if amount.is_nan() else template.copy()')],
 'bool_precision_bypasses_copy': [('working = template.copy()',
                                   'working = template if isinstance(precision, bool) else '
                                   'template.copy()')],
 'valid_max_precision_bypasses_copy': [('working = template.copy()',
                                        'working = template if precision > 1000 else '
                                        'template.copy()')],
 'invalid_precision_accepted': [('working.prec = precision', 'working.prec = max(1, precision)')],
 'precision_not_applied': [('working.prec = precision', 'pass')],
 'stale_flags_retained': [('working.clear_flags()', 'pass')],
 'inexact_trap_retained': [('working.traps[Inexact] = False', 'pass')],
 'unrelated_traps_cleared': [('working.traps[Inexact] = False', 'working.clear_traps()')],
 'rounding_reset': [('working.prec = precision',
                     "working.prec = precision\n    working.rounding = 'ROUND_HALF_EVEN'")],
 'lower_exponent_reset': [('working.prec = precision',
                           'working.prec = precision\n    working.Emin = -999999')],
 'upper_exponent_reset': [('working.prec = precision',
                           'working.prec = precision\n    working.Emax = 999999')],
 'capitals_reset': [('working.prec = precision',
                     'working.prec = precision\n    working.capitals = 1')],
 'clamp_reset': [('working.prec = precision', 'working.prec = precision\n    working.clamp = 0')],
 'computed_flags_lost': [('return result, working',
                          'working.clear_flags()\n    return result, working')],
 'return_alias_when_states_match': [('return result, working',
                                     'return result, template if (not any(working.flags.values()) '
                                     'and not any(template.flags.values()) and working.prec == '
                                     'template.prec and working.traps == template.traps) else '
                                     'working')],
 'exception_flags_written_back': [('result = working.quantize(amount, quantum)',
                                   'try:\n'
                                   '        result = working.quantize(amount, quantum)\n'
                                   '    except Exception:\n'
                                   '        template.flags = working.flags\n'
                                   '        raise')],
 'exception_traps_written_back': [('result = working.quantize(amount, quantum)',
                                   'try:\n'
                                   '        result = working.quantize(amount, quantum)\n'
                                   '    except Exception:\n'
                                   '        template.traps = working.traps\n'
                                   '        raise')],
 'exception_precision_written_back': [('result = working.quantize(amount, quantum)',
                                       'try:\n'
                                       '        result = working.quantize(amount, quantum)\n'
                                       '    except Exception:\n'
                                       '        template.prec = working.prec\n'
                                       '        raise')],
 'quantum_ignored': [('working.quantize(amount, quantum)',
                      "working.quantize(amount, Decimal('1'))")],
 'negative_amount_sign_lost': [('working.quantize(amount, quantum)',
                                'working.quantize(amount.copy_abs(), quantum)')]}

SAFE = {'unbound_context_copy': [('template.copy()', 'Context.copy(template)')],
 'standard_copy_protocol': [('from decimal import Context, Decimal, Inexact',
                             'from decimal import Context, Decimal, Inexact\n'
                             'from copy import copy'),
                            ('template.copy()', 'copy(template)')],
 'deepcopy_protocol': [('from decimal import Context, Decimal, Inexact',
                        'from decimal import Context, Decimal, Inexact\nfrom copy import deepcopy'),
                       ('template.copy()', 'deepcopy(template)')],
 'fresh_constructor': [('working = template.copy()',
                        'working = Context(prec=template.prec, rounding=template.rounding,\n'
                        '                      Emin=template.Emin, Emax=template.Emax,\n'
                        '                      capitals=template.capitals, clamp=template.clamp,\n'
                        '                      flags=dict(template.flags), '
                        'traps=dict(template.traps))')],
 'map_replacement': [('working.clear_flags()',
                      'working.flags = {signal: False for signal in working.flags}'),
                     ('working.traps[Inexact] = False',
                      'working.traps = {signal: enabled and signal is not Inexact\n'
                      '                     for signal, enabled in working.traps.items()}')],
 'configuration_reordered': [('working.prec = precision\n'
                              '    working.clear_flags()\n'
                              '    working.traps[Inexact] = False',
                              'working.traps[Inexact] = False\n'
                              '    working.clear_flags()\n'
                              '    working.prec = precision')],
 'decimal_method_form': [('working.quantize(amount, quantum)',
                          'amount.quantize(quantum, context=working)')],
 'return_independent_copy': [('return result, working', 'return result, working.copy()')],
 'other_rejection_type': [('working.prec = precision',
                           'try:\n'
                           '        working.prec = precision\n'
                           '    except (ValueError, OverflowError):\n'
                           "        raise ArithmeticError('precision') from None")],
 'list_result_container': [('return result, working', 'return [result, working]')]}

RACY = {}
