WEAKENED = {'원본 분리 생략': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)', 'RULE = BOOTSTRAP')],
 '공개 객체만 가변 복사': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                   'RULE = NameRule(BOOTSTRAP.pattern, BOOTSTRAP.flags)')],
 'pattern만 고정하여 flags 변경 허용': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                                'class _SealedRule:\n'
                                '    def __init__(self):\n'
                                '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                                '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                                '\n'
                                '    def __setattr__(self, name, value):\n'
                                '        if name == "pattern":\n'
                                '            raise ValueError(name)\n'
                                '        object.__setattr__(self, name, value)\n'
                                '\n'
                                '    def __delattr__(self, name):\n'
                                '        raise ValueError(name)\n'
                                '\n'
                                '    def fullmatch(self, name):\n'
                                '        return re.fullmatch(self.pattern, name, self.flags)\n'
                                '\n'
                                '\n'
                                'RULE = _SealedRule()')],
 'flags만 고정하여 pattern 변경 허용': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                                'class _SealedRule:\n'
                                '    def __init__(self):\n'
                                '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                                '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                                '\n'
                                '    def __setattr__(self, name, value):\n'
                                '        if name == "flags":\n'
                                '            raise ValueError(name)\n'
                                '        object.__setattr__(self, name, value)\n'
                                '\n'
                                '    def __delattr__(self, name):\n'
                                '        raise ValueError(name)\n'
                                '\n'
                                '    def fullmatch(self, name):\n'
                                '        return re.fullmatch(self.pattern, name, self.flags)\n'
                                '\n'
                                '\n'
                                'RULE = _SealedRule()')],
 '삭제 경로만 허용': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                'class _SealedRule:\n'
                '    def __init__(self):\n'
                '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                '\n'
                '    def __setattr__(self, name, value):\n'
                '        raise ValueError(name)\n'
                '\n'
                '    def __delattr__(self, name):\n'
                '        object.__delattr__(self, name)\n'
                '\n'
                '    def fullmatch(self, name):\n'
                '        return re.fullmatch(self.pattern, name, self.flags)\n'
                '\n'
                '\n'
                'RULE = _SealedRule()')],
 '상태 변경 후 setter 거절': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                        'class _SealedRule:\n'
                        '    def __init__(self):\n'
                        '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                        '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                        '\n'
                        '    def __setattr__(self, name, value):\n'
                        '        object.__setattr__(self, name, value)\n'
                        '        raise ValueError(name)\n'
                        '\n'
                        '    def __delattr__(self, name):\n'
                        '        raise ValueError(name)\n'
                        '\n'
                        '    def fullmatch(self, name):\n'
                        '        return re.fullmatch(self.pattern, name, self.flags)\n'
                        '\n'
                        '\n'
                        'RULE = _SealedRule()')],
 '읽기 전용 외피가 원본을 다시 읽음': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                          'class _LiveRule:\n'
                          '    __slots__ = ()\n'
                          '\n'
                          '    @property\n'
                          '    def pattern(self):\n'
                          '        return BOOTSTRAP.pattern\n'
                          '\n'
                          '    @property\n'
                          '    def flags(self):\n'
                          '        return BOOTSTRAP.flags\n'
                          '\n'
                          '    def fullmatch(self, name):\n'
                          '        return re.fullmatch(self.pattern, name, self.flags)\n'
                          '\n'
                          '\n'
                          'RULE = _LiveRule()')],
 '원본 사전만 변경 가능': [('BOOTSTRAP = NameRule()',
                   'BOOTSTRAP = NameRule()\n'
                   '\n'
                   '\n'
                   'class _Source:\n'
                   '    def __init__(self):\n'
                   '        self.__dict__.update(pattern=BOOTSTRAP.pattern, '
                   'flags=BOOTSTRAP.flags)\n'
                   '\n'
                   '    def __setattr__(self, name, value):\n'
                   '        raise AttributeError(name)\n'
                   '\n'
                   '    def __delattr__(self, name):\n'
                   '        raise AttributeError(name)\n'
                   '\n'
                   '\n'
                   'BOOTSTRAP = _Source()'),
                  ('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                   'class _LiveRule:\n'
                   '    __slots__ = ()\n'
                   '\n'
                   '    @property\n'
                   '    def pattern(self):\n'
                   '        return BOOTSTRAP.pattern\n'
                   '\n'
                   '    @property\n'
                   '    def flags(self):\n'
                   '        return BOOTSTRAP.flags\n'
                   '\n'
                   '    def fullmatch(self, name):\n'
                   '        return re.fullmatch(self.pattern, name, self.flags)\n'
                   '\n'
                   '\n'
                   'RULE = _LiveRule()')],
 '얕은 복사 시 기존 규칙 변경': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                       'class _SealedRule:\n'
                       '    def __init__(self):\n'
                       '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                       '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                       '\n'
                       '    def __setattr__(self, name, value):\n'
                       '        raise ValueError(name)\n'
                       '\n'
                       '    def __delattr__(self, name):\n'
                       '        raise ValueError(name)\n'
                       '\n'
                       '    def __copy__(self):\n'
                       '        object.__setattr__(self, "flags", re.IGNORECASE)\n'
                       '        return self\n'
                       '\n'
                       '    def fullmatch(self, name):\n'
                       '        return re.fullmatch(self.pattern, name, self.flags)\n'
                       '\n'
                       '\n'
                       'RULE = _SealedRule()')],
 '깊은 복사 시 기존 규칙 변경': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                       'class _SealedRule:\n'
                       '    def __init__(self):\n'
                       '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                       '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                       '\n'
                       '    def __setattr__(self, name, value):\n'
                       '        raise ValueError(name)\n'
                       '\n'
                       '    def __delattr__(self, name):\n'
                       '        raise ValueError(name)\n'
                       '\n'
                       '    def __deepcopy__(self, memo):\n'
                       '        object.__setattr__(self, "flags", re.IGNORECASE)\n'
                       '        return self\n'
                       '\n'
                       '    def fullmatch(self, name):\n'
                       '        return re.fullmatch(self.pattern, name, self.flags)\n'
                       '\n'
                       '\n'
                       'RULE = _SealedRule()')],
 '소비자만 고정하고 반환 객체 가변': [('    return RULE\n',
                         '    return NameRule(r"JOB-(?P<serial>[0-9]{4})", re.ASCII)\n')],
 '가드 참조 우회': [('return RULE.fullmatch(name) is not None',
               'return BOOTSTRAP.fullmatch(name) is not None')],
 '대소문자 경계 약화': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                 'RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags | re.IGNORECASE)')],
 'ASCII 숫자 경계 약화': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                     'RULE = re.compile(r"JOB-(?P<serial>[\\d]{4})")')],
 '일반 Enum 문자열을 str로 재변환': [('return RULE.fullmatch(name) is not None',
                            'return RULE.fullmatch(str(name)) is not None')],
 '별도 작성용 객체 생성이 게시된 규칙을 변경': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                               'class _LiveRule:\n'
                               '    __slots__ = ()\n'
                               '\n'
                               '    @property\n'
                               '    def pattern(self):\n'
                               '        return BOOTSTRAP.pattern\n'
                               '\n'
                               '    @property\n'
                               '    def flags(self):\n'
                               '        return BOOTSTRAP.flags\n'
                               '\n'
                               '    def fullmatch(self, name):\n'
                               '        return re.fullmatch(self.pattern, name, self.flags)\n'
                               '\n'
                               '\n'
                               'RULE = _LiveRule()'),
                              ('    flags: int = re.ASCII\n',
                               '    flags: int = re.ASCII\n'
                               '\n'
                               '    def __post_init__(self):\n'
                               '        if "BOOTSTRAP" in globals():\n'
                               '            BOOTSTRAP.pattern = self.pattern\n'
                               '            BOOTSTRAP.flags = self.flags\n')]}

SAFE = {'명명 그룹을 비포획 그룹으로 교체': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                         'RULE = re.compile(r"JOB-(?:[0-9]{4})", BOOTSTRAP.flags)')],
 '동치 숫자 문자 클래스': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                   'RULE = re.compile(r"JOB-(?P<serial>[0123456789]{4})", BOOTSTRAP.flags)')],
 '불필요한 ASCII 플래그 제거': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                        'RULE = re.compile(BOOTSTRAP.pattern)')],
 '컴파일 함수 import 별칭': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                       'from re import compile as build_rule\n'
                       'RULE = build_rule(BOOTSTRAP.pattern, BOOTSTRAP.flags)')],
 '원본을 먼저 복사': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                'from copy import deepcopy\n'
                '_snapshot = deepcopy(BOOTSTRAP)\n'
                'RULE = re.compile(_snapshot.pattern, _snapshot.flags)')],
 '다른 불변 외피와 거절 예외': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
                      'class _SealedRule:\n'
                      '    def __init__(self):\n'
                      '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
                      '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
                      '\n'
                      '    def __setattr__(self, name, value):\n'
                      '        raise ValueError(name)\n'
                      '\n'
                      '    def __delattr__(self, name):\n'
                      '        raise ValueError(name)\n'
                      '\n'
                      '    def fullmatch(self, name):\n'
                      '        return re.fullmatch(self.pattern, name, self.flags)\n'
                      '\n'
                      '\n'
                      'RULE = _SealedRule()')],
 '다른 거절 예외': [('RULE = re.compile(BOOTSTRAP.pattern, BOOTSTRAP.flags)',
               'class _SealedRule:\n'
               '    def __init__(self):\n'
               '        object.__setattr__(self, "pattern", BOOTSTRAP.pattern)\n'
               '        object.__setattr__(self, "flags", BOOTSTRAP.flags)\n'
               '\n'
               '    def __setattr__(self, name, value):\n'
               '        raise RuntimeError(name)\n'
               '\n'
               '    def __delattr__(self, name):\n'
               '        raise RuntimeError(name)\n'
               '\n'
               '    def fullmatch(self, name):\n'
               '        return re.fullmatch(self.pattern, name, self.flags)\n'
               '\n'
               '\n'
               'RULE = _SealedRule()')]}

RACY = {}
