WEAKENED = {'retry/bypass_revision': [('if self._state[1] == revision:', 'if True:')],
 'retry/reacquire_revision': [('self._commit(revision, delta)',
                               'self._commit(self._state[1], delta)')],
 'retry/assert_only': [('        if self._state[1] == revision:\n'
                        '            self._state = (self._state[0] + delta, revision + 1)',
                        '        assert self._state[1] == revision\n'
                        '        self._state = (self._state[0] + delta, revision + 1)')],
 'retry/no_revision_increment': [('self._state = (self._state[0] + delta, revision + 1)',
                                  'self._state = (self._state[0] + delta, revision)')],
 'revision/increment_twice': [('revision + 1)', 'revision + 2)')],
 'history/fresh_revision_only': [('revision = self._state[1]', 'revision = 0')],
 'history/deduplicate_delta_across_requests': [('if self._state[1] == revision:',
                                                'if self._state[1] == revision and getattr(self, '
                                                "'_last_delta', None) != delta:"),
                                               ('self._state = (self._state[0] + delta, revision + '
                                                '1)',
                                                'self._state = (self._state[0] + delta, revision + '
                                                '1)\n'
                                                '            self._last_delta = delta')],
 'construction/discard_initial': [('(int(initial), 0)', '(0, 0)')],
 'construction/negative_initial': [('(int(initial), 0)', '(abs(int(initial)), 0)')],
 'construction/large_initial': [('(int(initial), 0)', '(int(initial) % (2**64), 0)')],
 'construction/nonzero_revision': [('(int(initial), 0)', '(int(initial), 1)')],
 'construction/reject_subtypes': [('self._state = (int(initial), 0)',
                                   'self._state = (int(initial) if type(initial) is int else 0, '
                                   '0)')],
 'delta/negative': [('delta = int(delta)', 'delta = abs(int(delta))')],
 'delta/large': [('delta = int(delta)', 'delta = max(-(2**63), min(2**63 - 1, int(delta)))')],
 'delta/zero': [('if self._state[1] == revision:',
                 'if self._state[1] == revision and delta != 0:')],
 'delta/subtypes': [('delta = int(delta)', 'delta = int(delta) if type(delta) is int else 0')],
 'attempts/zero': [('range(attempts)', 'range(max(1, attempts))')],
 'attempts/negative': [('range(attempts)', 'range(abs(attempts))')],
 'attempts/one': [('range(attempts)', 'range(attempts - 1)')],
 'attempts/large': [('for _ in range(attempts):',
                     'for _ in range(min(attempts, 2**63 - 1) if attempts <= 2**63 - 1 else 0):')],
 'attempts/subtypes': [('range(attempts)', 'range(attempts if type(attempts) is int else 0)')],
 'observation/ack_before_commit': [('            self._commit(revision, delta)\n'
                                    '            try:\n'
                                    '                acknowledge()',
                                    '            try:\n'
                                    '                acknowledge()\n'
                                    '                self._commit(revision, delta)')],
 'exception/rollback_after_timeout': [('except TimeoutError:\n                pass',
                                       'except TimeoutError:\n'
                                       '                self._state = (self._state[0] - delta, '
                                       'revision)')],
 'exception/rollback_after_other_exception': [('            except TimeoutError:\n'
                                               '                pass',
                                               '            except TimeoutError:\n'
                                               '                pass\n'
                                               '            except Exception:\n'
                                               '                self._state = (self._state[0] - '
                                               'delta, revision)\n'
                                               '                raise')],
 'exception/rollback_after_base_exception': [('            except TimeoutError:\n'
                                              '                pass',
                                              '            except TimeoutError:\n'
                                              '                pass\n'
                                              '            except BaseException as error:\n'
                                              '                if not isinstance(error, '
                                              'Exception):\n'
                                              '                    self._state = (self._state[0] - '
                                              'delta, revision)\n'
                                              '                raise')],
 'history/revision_wrap': [('revision + 1)', '(revision + 1) % 256)')],
 'history/shared_state': [('self._state = (int(initial), 0)', 'Balance._state = (int(initial), 0)'),
                          ('self._state = (self._state[0] + delta, revision + 1)',
                           'Balance._state = (self._state[0] + delta, revision + 1)')],
 'observation/temporary_rollback_only_during_callback': [('                acknowledge()',
                                                          '                committed = '
                                                          'self._state\n'
                                                          '                self._state = '
                                                          '(committed[0] - delta, revision)\n'
                                                          '                try:\n'
                                                          '                    acknowledge()\n'
                                                          '                finally:\n'
                                                          '                    self._state = '
                                                          'committed')],
 'observation/corrupt_only_after_successful_callback': [('                acknowledge()\n'
                                                         '                return',
                                                         '                acknowledge()\n'
                                                         '                self._state = '
                                                         '(self._state[0] + 1, self._state[1])\n'
                                                         '                return')],
 'history/reset_revision_on_no_attempt': [('        delta = int(delta)',
                                           '        if attempts <= 0:\n'
                                           '            self._state = (self._state[0], 0)\n'
                                           '        delta = int(delta)')]}

SAFE = {'branch/early_return': [('        if self._state[1] == revision:\n'
                          '            self._state = (self._state[0] + delta, revision + 1)',
                          '        if self._state[1] != revision:\n'
                          '            return\n'
                          '        self._state = (self._state[0] + delta, revision + 1)')],
 'branch/order_comparison': [('self._state[1] == revision', 'revision == self._state[1]')],
 'container/list': [('self._state = (int(initial), 0)', 'self._state = [int(initial), 0]'),
                    ('self._state = (self._state[0] + delta, revision + 1)',
                     'self._state = [self._state[0] + delta, revision + 1]'),
                    ('return self._state', 'return list(self._state)')],
 'exception/exhaustion_type': [('raise TimeoutError("confirmation unavailable")',
                                'raise RuntimeError("confirmation unavailable")')],
 'exception/propagate_ack_timeout': [('except TimeoutError:\n                pass',
                                      'except TimeoutError:\n                raise')],
 'normalization/plain_subtypes': [('(int(initial), 0)', '(initial, 0)'),
                                  ('delta = int(delta)', 'delta = delta + 0')],
 'attempts/nonpositive_return': [('        delta = int(delta)',
                                  '        if attempts <= 0:\n'
                                  '            return\n'
                                  '        delta = int(delta)')],
 'return/value': [('                return', '                return self.snapshot()')]}

RACY = {}
