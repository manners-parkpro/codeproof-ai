AXES = {'invalid_negative_anywhere': ['exhaustive mixed signs; long negative tail',
                               'negative_tail_unchecked',
                               'negative_far_tail_ignored'],
 'invalid_ticket_endpoints': ['-1, total, total+1',
                              'negative_ticket_admitted',
                              'total_endpoint_admitted'],
 'empty_and_zero_total': ['empty; all-zero lists',
                          'empty_input_admitted',
                          'all_zero_input_admitted'],
 'half_open_partition': ['each cumulative boundary and its neighbors',
                         'positive_boundary_belongs_to_previous',
                         'zero_bucket_selected'],
 'interior_and_order': ['exhaustive unequal weights and interior tickets',
                        'remaining_rebased_one_too_far',
                        'order_discarded'],
 'original_index': ['leading/interior zero weights',
                    'zero_indices_compressed',
                    'index_one_based'],
 'arbitrary_magnitude': ['2**53+1; 2**63+1; 10**400',
                         'float_ticket',
                         'signed_64_bit_weight_limit'],
 'ordinary_subtypes': ['bool; IntEnum; PlainInt; PlainList in both argument '
                       'positions',
                       'ticket_subtypes_rejected',
                       'weight_subtypes_rejected',
                       'list_subtypes_rejected'],
 'arbitrary_length': ['31,128,513 zero/one-weight entries',
                      'long_input_truncated'],
 'preservation_success_and_rejection': ['identity snapshot on both paths',
                                        'successful_call_consumes_weight',
                                        'failed_call_sorts_input',
                                        'negative_rejection_clears_input'],
 'unspecified_choices': ['exception type; local container; integer '
                         'normalization; loop algorithm',
                         'different_rejection_type',
                         'tuple_snapshot',
                         'prefix_sum_algorithm']}

WEAKENED = {'negative_weights_unchecked': [('any(weight < 0 for weight in weights)', 'False')],
 'negative_tail_unchecked': [('any(weight < 0 for weight in weights)',
                              'any(weight < 0 for weight in weights[:1])')],
 'only_all_negative_rejected': [('any(weight < 0 for weight in weights)',
                                 'all(weight < 0 for weight in weights)')],
 'negative_ticket_admitted': [('ticket < 0 or ticket >= sum(weights)', 'ticket >= sum(weights)')],
 'empty_input_admitted': [('    if any(weight < 0 for weight in weights):',
                           '    if not weights:\n'
                           '        return 0\n'
                           '    if any(weight < 0 for weight in weights):')],
 'all_zero_input_admitted': [('    if any(weight < 0 for weight in weights):',
                              '    if weights and all(weight == 0 for weight in weights):\n'
                              '        return 0\n'
                              '    if any(weight < 0 for weight in weights):')],
 'total_endpoint_admitted': [('ticket < 0 or ticket >= sum(weights)',
                              'ticket < 0 or ticket > sum(weights)'),
                             ('raise RuntimeError("unassigned ticket")',
                              'return len(weights) - 1')],
 'twin_boundary_belongs_to_previous': [('remaining >= weight', 'remaining > weight')],
 'positive_boundary_belongs_to_previous': [('remaining >= weight',
                                            'remaining > weight or weight == 0')],
 'zero_bucket_selected': [('remaining >= weight', 'remaining >= weight and weight != 0')],
 'left_endpoint_rejected': [('ticket < 0 or ticket >= sum(weights)',
                             'ticket <= 0 or ticket >= sum(weights)')],
 'last_valid_ticket_rejected': [('ticket < 0 or ticket >= sum(weights)',
                                 'ticket < 0 or ticket >= sum(weights) - 1')],
 'remaining_not_rebased': [('remaining -= weight', 'remaining -= 0')],
 'remaining_rebased_one_too_far': [('remaining -= weight', 'remaining -= weight + 1')],
 'index_one_based': [('return index', 'return index + 1')],
 'order_discarded': [('enumerate(weights)', 'enumerate(sorted(weights))')],
 'zero_indices_compressed': [('enumerate(weights)',
                              'enumerate(weight for weight in weights if weight)')],
 'float_ticket': [('remaining = ticket', 'remaining = float(ticket)')],
 'signed_64_bit_weight_limit': [('weight < 0 for weight in weights',
                                 'weight < 0 or weight > 2**63 - 1 for weight in weights')],
 'ticket_subtypes_rejected': [('    remaining = ticket',
                               '    if type(ticket) is not int:\n'
                               '        raise TypeError("ticket type")\n'
                               '    remaining = ticket')],
 'weight_subtypes_rejected': [('    remaining = ticket',
                               '    if any(type(weight) is not int for weight in weights):\n'
                               '        raise TypeError("weight type")\n'
                               '    remaining = ticket')],
 'list_subtypes_rejected': [('    remaining = ticket',
                             '    if type(weights) is not list:\n'
                             '        raise TypeError("weights type")\n'
                             '    remaining = ticket')],
 'long_input_truncated': [('enumerate(weights)', 'enumerate(weights[:128])')],
 'negative_far_tail_ignored': [('weight < 0 for weight in weights',
                                'weight < 0 for weight in weights[:128]')],
 'successful_call_consumes_weight': [('        return index',
                                      '        weights[index] = 0\n        return index')],
 'failed_call_sorts_input': [('        raise ValueError("ticket out of range")',
                              '        weights.sort()\n'
                              '        raise ValueError("ticket out of range")')],
 'negative_rejection_clears_input': [('        raise ValueError("negative weight")',
                                      '        weights.clear()\n'
                                      '        raise ValueError("negative weight")')]}

SAFE = {'different_rejection_type': [('raise ValueError("negative weight")',
                               'raise ArithmeticError("negative weight")'),
                              ('raise ValueError("ticket out of range")',
                               'raise LookupError("ticket out of range")')],
 'tuple_snapshot': [('    if any(weight < 0 for weight in weights):',
                     '    weights = tuple(weights)\n'
                     '    if any(weight < 0 for weight in weights):')],
 'normalize_local_integers': [('    if any(weight < 0 for weight in weights):',
                               '    weights = [int(weight) for weight in weights]\n'
                               '    ticket = int(ticket)\n'
                               '    if any(weight < 0 for weight in weights):')],
 'equivalent_integer_boundary': [('remaining >= weight', 'remaining > weight - 1')],
 'equivalent_zero_handling': [('    for index, weight in enumerate(weights):',
                               '    for index, weight in enumerate(weights):\n'
                               '        if weight == 0:\n'
                               '            continue')],
 'redundant_upper_check_removed': [('ticket < 0 or ticket >= sum(weights)', 'ticket < 0')],
 'prefix_sum_algorithm': [('    remaining = ticket\n'
                           '    for index, weight in enumerate(weights):\n'
                           '        if remaining >= weight:\n'
                           '            remaining -= weight\n'
                           '            continue\n'
                           '        return index',
                           '    right = 0\n'
                           '    for index, weight in enumerate(weights):\n'
                           '        right += weight\n'
                           '        if ticket < right:\n'
                           '            return index')]}

RACY = {}
