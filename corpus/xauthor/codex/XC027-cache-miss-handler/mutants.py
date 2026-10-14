CLAIM_AXES = {'path values': ['empty',
                 'relative',
                 'absolute',
                 'parent components',
                 'unicode',
                 'escaped newline',
                 'escaped null',
                 'long'],
 'path types': ['str', 'ordinary str subclass', '(str, Enum)'],
 'operation result': ['success',
                      'FileNotFoundError',
                      'subclass',
                      'other OSError',
                      'non-OSError'],
 'operation stage': ['open',
                     'enter',
                     'read',
                     'exit',
                     'read error replaced by exit error'],
 'unspecified behavior': ['exception propagation',
                          'return value',
                          'catch spelling',
                          'imports']}

WEAKENED = {'catch narrowed to permissions': [('except OSError:', 'except PermissionError:')],
 'missing file handler moved first': [('    except OSError:\n'
                                       '        return None\n'
                                       '    except FileNotFoundError:\n'
                                       '        shutil.rmtree(os.path.dirname(cache_file))\n'
                                       '        return None\n',
                                       '    except FileNotFoundError:\n'
                                       '        shutil.rmtree(os.path.dirname(cache_file))\n'
                                       '        return None\n'
                                       '    except OSError:\n'
                                       '        return None\n')],
 'empty path bypass': [('except OSError:', 'except (OSError if cache_file else PermissionError):')],
 'ordinary str subtype bypass': [('except OSError:',
                                  'except (OSError if type(cache_file) is str or '
                                  "isinstance(cache_file, __import__('enum').Enum) else "
                                  'PermissionError):')],
 'standard enum str bypass': [('except OSError:',
                               'except (PermissionError if isinstance(cache_file, '
                               "__import__('enum').Enum) else OSError):")],
 'large path bypass': [('except OSError:',
                        'except (OSError if len(cache_file) < 4096 else PermissionError):')],
 'embedded null bypass': [('except OSError:',
                           "except (PermissionError if '\\x00' in cache_file else OSError):")],
 'nonascii path bypass': [('except OSError:',
                           'except (OSError if cache_file.isascii() else PermissionError):')],
 'read and exit bypass': [('except OSError:',
                           "except (PermissionError if 'stream' in locals() else OSError):")],
 'only exact missing class absorbed': [('    except OSError:\n        return None\n',
                                        '    except OSError as error:\n'
                                        '        if isinstance(error, FileNotFoundError) and '
                                        'type(error) is not FileNotFoundError:\n'
                                        '            shutil.rmtree(os.path.dirname(cache_file))\n'
                                        '        return None\n')],
 'missing filename bypass': [('    except OSError:\n        return None\n',
                              '    except OSError as error:\n'
                              '        if isinstance(error, FileNotFoundError) and '
                              'error.filename:\n'
                              '            shutil.rmtree(os.path.dirname(cache_file))\n'
                              '        return None\n')]}

SAFE = {'IOError alias': [('except OSError:', 'except IOError:')],
 'broader handler': [('except OSError:', 'except Exception:')],
 'tuple handler': [('except OSError:', 'except (OSError, ValueError):')],
 'guard pass still excludes sibling': [('    except OSError:\n        return None\n',
                                        '    except OSError:\n        pass\n')],
 'guard reraises without sibling dispatch': [('    except OSError:\n        return None\n',
                                              '    except OSError:\n        raise\n')],
 'different rejection result': [('    except OSError:\n        return None\n',
                                 "    except OSError:\n        return b''\n")],
 'module import alias': [('import shutil', 'import shutil as fs'),
                         ('shutil.rmtree(', 'fs.rmtree(')],
 'direct sink import': [('import shutil', 'from shutil import rmtree'),
                        ('shutil.rmtree(', 'rmtree(')],
 'direct open alias': [('import os', 'import os\nfrom builtins import open as cache_open'),
                       ('with open(', 'with cache_open(')],
 'explicit error binding': [('except OSError:', 'except OSError as error:')]}

RACY = {}

