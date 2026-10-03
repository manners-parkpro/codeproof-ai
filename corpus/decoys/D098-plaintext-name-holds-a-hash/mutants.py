"""D098 변이 - 쓰는 단계 6개 · 검토 0개 (약화 5 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '원문 저장 (twin 꼴)': [
        ('    plaintext = hashlib.pbkdf2_hmac("sha256", secret, salt, _ROUNDS)\n', '    plaintext = secret\n'),
    ],
    '소금 없는 sha256': [
        ('    plaintext = hashlib.pbkdf2_hmac("sha256", secret, salt, _ROUNDS)\n', '    plaintext = hashlib.sha256(secret).digest()\n'),
    ],
    '고정 소금': [
        ('    salt = os.urandom(_SALT_BYTES)\n', '    salt = b"\\x00" * _SALT_BYTES\n'),
    ],
    '반복 1000번': [
        ('_ROUNDS = 600_000\n', '_ROUNDS = 1000\n'),
    ],
    '사용자에서 정한 소금': [
        ('    salt = os.urandom(_SALT_BYTES)\n', '    salt = hashlib.md5(user.encode()).digest()\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'secrets 로 소금 (안전)': [
        ('import os\n', 'import os\nimport secrets\n'),
        ('    salt = os.urandom(_SALT_BYTES)\n', '    salt = secrets.token_bytes(_SALT_BYTES)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
