WEAKENED: dict[str, list[tuple[str, str]]] = {'empty_buffer_archive_fallback': [('        return b""',
                                    '        with open(archive_path, "rb") as archive:\n'
                                    '            return archive.read()')],
 'negative_sequence_skips_modulo': [('index = sequence % size',
                                     'index = sequence if sequence < 0 else sequence % size')],
 'signed_remainder': [('index = sequence % size',
                       'index = sequence % size if sequence >= 0 else -((-sequence) % size)')],
 'signed_byte_index': [('index = sequence % size',
                        'index = ((sequence % size + 128) % 256) - 128')],
 'oversized_integer_bypass': [('index = sequence % size',
                               'index = sequence if sequence.bit_length() > 64 else sequence % '
                               'size')],
 'minimum_signed_integer_bypass': [('index = sequence % size',
                                    'index = sequence if sequence == -(1 << 63) else sequence % '
                                    'size')],
 'integer_subtype_bypass': [('index = sequence % size',
                             'index = sequence % size if type(sequence) is int else sequence')],
 'singleton_fast_path': [('index = sequence % size',
                          'index = sequence if size == 1 else sequence % size')],
 'nonpower_buffer_bypass': [('index = sequence % size',
                             'index = sequence if size & (size - 1) else sequence % size')],
 'large_buffer_bypass': [('index = sequence % size',
                          'index = sequence % size if size <= 256 else sequence')],
 'list_subtype_bypass': [('index = sequence % size',
                          'index = sequence % size if type(records) is list else sequence')],
 'negative_divisor': [('index = sequence % size', 'index = sequence % -size')],
 'centered_remainder': [('index = sequence % size',
                         'index = (sequence + size // 2) % size - size // 2')]}

SAFE: dict[str, list[tuple[str, str]]] = {'divmod_remainder': [('index = sequence % size', 'index = divmod(sequence, size)[1]')],
 'floor_quotient_remainder': [('index = sequence % size',
                               'index = sequence - (sequence // size) * size')],
 'absolute_divisor': [('index = sequence % size', 'index = sequence % abs(size)')],
 'nonpositive_empty_check': [('if size == 0:', 'if size <= 0:')],
 'empty_rejected_with_lookup_error': [('return b""', 'raise LookupError("empty ring")')],
 'empty_rejected_with_runtime_error': [('return b""', 'raise RuntimeError("empty ring")')],
 'tuple_snapshot': [('    size = len(records)',
                     '    records = tuple(records)\n    size = len(records)')],
 'builtin_module_import': [('        with open(archive_path, "rb") as archive:',
                            '        import builtins\n'
                            '        with builtins.open(archive_path, "rb") as archive:')],
 'io_alias_import': [('\n\n\ndef read_record',
                      '\n\nfrom io import open as archive_open\n\n\ndef read_record'),
                     ('with open(archive_path, "rb")', 'with archive_open(archive_path, "rb")')],
 'canonical_integer': [('index = sequence % size', 'index = int(sequence) % size')]}

RACY: dict[str, list[tuple[str, str]]] = {}
