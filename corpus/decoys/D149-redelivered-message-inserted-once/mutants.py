"""D149 변이 - 쓰는 단계 15개 · 쓰는 단계 점검 26개 · 독립 검토 4개 · 교차 1개 (약화 32 · 안전 14 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_SCHEMA = '_SCHEMA = "CREATE TABLE IF NOT EXISTS deliveries (message_id TEXT NOT NULL, body TEXT NOT NULL)"\n'
_RECORD = (
    "_RECORD = (\n"
    '    "INSERT INTO deliveries (message_id, body) SELECT :id, :body"\n'
    '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n'
    ")\n"
)
_GUARD = '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n'
_EXEC = '            conn.execute(_RECORD, {"id": message_id, "body": body})\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[다시 배달] 매번 넣음 (twin)": [(_RECORD, '_RECORD = (\n    "INSERT INTO deliveries (message_id, body)"\n    " VALUES (:id, :body)"\n)\n')],
    "[다시 배달] 두 줄까지 넣음": [(_GUARD, '    " WHERE (SELECT count(*) FROM deliveries WHERE message_id = :id) < 2"\n')],
    "[처음 body] 다시 오면 body 를 바꿈": [
        (_EXEC, '            conn.execute("UPDATE deliveries SET body = :body WHERE message_id = :id", {"id": message_id, "body": body})\n' + _EXEC),
    ],
    "[다른 id] 다른 message_id 의 줄을 지움": [
        (_EXEC, '            conn.execute("DELETE FROM deliveries WHERE message_id <> :id", {"id": message_id})\n' + _EXEC),
    ],
    "[같음] 대소문자를 무시": [(_GUARD, '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id COLLATE NOCASE)"\n')],
    "[같음] 앞뒤 공백을 무시": [(_GUARD, '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE trim(message_id) = trim(:id))"\n')],
    "[같음] LIKE 로 비교": [(_GUARD, '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id LIKE :id)"\n')],
    "[같음] 숫자 친화 칸": [(_SCHEMA, _SCHEMA.replace("message_id TEXT", "message_id NUMERIC"))],
    "[같음] NUL 뒤를 버림": [(_EXEC, '            conn.execute(_RECORD, {"id": message_id.partition(chr(0))[0], "body": body})\n')],
    "[예외 없이] 바인딩 실패를 삼킴": [
        (_EXEC, "            try:\n    " + _EXEC + "            except UnicodeEncodeError:\n                pass\n"),
    ],
    "[예외] 줄부터 커밋하고 body 를 채움": [
        (
            _EXEC,
            '            conn.execute(_RECORD, {"id": message_id, "body": ""})\n'
            "            conn.commit()\n"
            "            conn.execute(\"UPDATE deliveries SET body = :body WHERE message_id = :id AND body = ''\", {\"id\": message_id, \"body\": body})\n",
        ),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[같음] NFC 로 정규화': [('import sqlite3\n', 'import sqlite3\nimport unicodedata\n'), ('{"id": message_id, "body": body}', '{"id": unicodedata.normalize("NFC", message_id), "body": body}')],
    '[같음] NFKC 로 정규화': [('import sqlite3\n', 'import sqlite3\nimport unicodedata\n'), ('{"id": message_id, "body": body}', '{"id": unicodedata.normalize("NFKC", message_id), "body": body}')],
    '[같음] body 가 같으면 같은 메시지로 침': [('    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n', '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id OR body = :body)"\n')],
    '[그 뒤로] 최근 20 줄만 봄': [('    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n', '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id AND rowid > (SELECT max(rowid) FROM deliveries) - 20)"\n')],
    '[하위 타입] str() 로 바꿔 넣음': [('{"id": message_id, "body": body}', '{"id": str(message_id), "body": str(body)}')],
    '[하위 타입] f-string 으로 바꿔 넣음': [('{"id": message_id, "body": body}', '{"id": f"{message_id}", "body": f"{body}"}')],
    '[늘 거절] 모든 부름을 거절': [('    with closing(sqlite3.connect(path)) as conn:\n', '    raise ValueError("쓰지 않는다")\n    with closing(sqlite3.connect(path)) as conn:\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[같음] lower() 로 비교': [('    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n', '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE lower(message_id) = lower(:id))"\n')],
    '[같음] 밑줄을 버리고 비교': [('    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n', '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE replace(message_id, \'_\', \'\') = replace(:id, \'_\', \'\'))"\n')],
    '[빈 id] 빈 message_id 는 조용히 버림': [('    with closing(sqlite3.connect(path)) as conn:\n', '    if not message_id:\n        return\n    with closing(sqlite3.connect(path)) as conn:\n')],
    '[같음] 새 파일을 UTF-16 으로 만듦': [('            conn.execute(_SCHEMA)\n', '            conn.execute("PRAGMA encoding = \'UTF-16le\'")\n            conn.execute(_SCHEMA)\n')],
    '[같음] NFD 로 정규화': [('import sqlite3\n', 'import sqlite3\nimport unicodedata\n'), ('{"id": message_id, "body": body}', '{"id": unicodedata.normalize("NFD", message_id), "body": body}')],
    '[예외] 실패하면 그 id 의 줄을 지움': [('            conn.execute(_RECORD, {"id": message_id, "body": body})\n', '            try:\n                conn.execute(_RECORD, {"id": message_id, "body": body})\n            except UnicodeEncodeError:\n                conn.execute("DELETE FROM deliveries WHERE message_id = :id", {"id": message_id})\n                conn.commit()\n                raise\n')],
    '[다른 id] 표지 줄을 같은 표에 남김': [('            conn.execute(_RECORD, {"id": message_id, "body": body})\n', '            conn.execute(_RECORD, {"id": message_id, "body": body})\n            conn.execute("DELETE FROM deliveries WHERE message_id = \'#last\'")\n            conn.execute("INSERT INTO deliveries (message_id, body) VALUES (\'#last\', :id)", {"id": message_id})\n')],
    '[인코딩] UTF-8 확인 없음 (점검 앞의 decoy)': [('        if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":\n            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n', '')],
    '[인코딩] UTF-16 만 거절 - 다른 UTF-16 꼴은 받음': [('        if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":\n', '        if conn.execute("PRAGMA encoding").fetchone()[0] == "UTF-16":\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[인코딩] UTF-16le 만 거절 - UTF-16be 파일에는 써서 비문자 id 가 U+FFFD 로 합쳐짐': [('        if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":\n            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n', '        if conn.execute("PRAGMA encoding").fetchone()[0] == "UTF-16le":\n            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n')],
    '[-O] 인코딩 확인을 assert 로 - python -O 에서는 UTF-16 파일에 씀': [('        if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":\n            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n', '        assert conn.execute("PRAGMA encoding").fetchone()[0] == "UTF-8", "UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다"\n')],
    '[id] 앞 64자로 잘라 담음 - 앞부분이 같은 긴 id 가 한 줄이 됨': [('            conn.execute(_RECORD, {"id": message_id, "body": body})\n', '            conn.execute(_RECORD, {"id": message_id[:64], "body": body})\n')],
    '[id] 서식 문자(Cf)를 지우고 담음 - ab 와 a+U+200B+b 가 한 줄이 됨': [('            conn.execute(_RECORD, {"id": message_id, "body": body})\n', '            conn.execute(_RECORD, {"id": "".join(ch for ch in message_id if unicodedata.category(ch) != "Cf"), "body": body})\n'), ('import sqlite3\n', 'import sqlite3\nimport unicodedata\n')],
    # 교차 렌즈 - 원래 증명이 놓치던 약화
    '[파일] 다른 표가 있는 기존 파일은 거절 - 다른 표를 둔 UTF-8 파일에 쓸 수 없음': [('            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n', '            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n        if conn.execute("SELECT count(*) FROM sqlite_master WHERE name NOT IN (\'deliveries\', \'deliveries_message_id\')").fetchone()[0]:\n            raise ValueError("다른 표가 있는 파일에는 쓰지 않는다")\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "NOT IN 으로 거름 (안전)": [(_GUARD, '    " WHERE :id NOT IN (SELECT message_id FROM deliveries)"\n')],
    "UNIQUE 와 ON CONFLICT DO NOTHING (안전)": [
        (_SCHEMA, _SCHEMA.replace("message_id TEXT NOT NULL", "message_id TEXT NOT NULL UNIQUE")),
        (_RECORD, '_RECORD = "INSERT INTO deliveries (message_id, body) VALUES (:id, :body) ON CONFLICT (message_id) DO NOTHING"\n'),
    ],
    "자리 표시자를 ? 로 (안전)": [
        ('SELECT :id, :body"', 'SELECT ?, ?"'),
        ("WHERE message_id = :id)", "WHERE message_id = ?)"),
        ('{"id": message_id, "body": body}', "(message_id, body, message_id)"),
    ],
    "존재만 묻는 LIMIT 1 (안전)": [(_GUARD, '    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id LIMIT 1)"\n')],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[트랜잭션] autocommit=False': [('sqlite3.connect(path)', 'sqlite3.connect(path, autocommit=False)')],
    '[제약] UNIQUE 색인과 INSERT OR IGNORE': [('            conn.execute(_SCHEMA)\n', '            conn.execute(_SCHEMA)\n            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS deliveries_message_id ON deliveries (message_id)")\n'), ('_RECORD = (\n    "INSERT INTO deliveries (message_id, body) SELECT :id, :body"\n    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n)\n', '_RECORD = "INSERT OR IGNORE INTO deliveries (message_id, body) VALUES (:id, :body)"\n')],
    '[import 꼴] contextlib · sqlite3 별칭': [('import sqlite3\nfrom contextlib import closing\n', 'import contextlib\nimport sqlite3 as _sqlite\n'), ('    with closing(sqlite3.connect(path)) as conn:\n', '    with contextlib.closing(_sqlite.connect(path)) as conn:\n')],
    '[예외 타입] 바인딩 실패를 RuntimeError 로 감쌈': [('            conn.execute(_RECORD, {"id": message_id, "body": body})\n', '            try:\n                conn.execute(_RECORD, {"id": message_id, "body": body})\n            except UnicodeEncodeError as exc:\n                raise RuntimeError("UTF-8 로 못 바꾸는 글자") from exc\n')],
    '[컨테이너] executemany 에 한 줄 목록': [('conn.execute(_RECORD, {"id": message_id, "body": body})', 'conn.executemany(_RECORD, [{"id": message_id, "body": body}])')],
    '[다른 구현] count(*) = 0': [('    " WHERE NOT EXISTS (SELECT 1 FROM deliveries WHERE message_id = :id)"\n', '    " WHERE (SELECT count(*) FROM deliveries WHERE message_id = :id) = 0"\n')],
    '[하위 타입] str.__str__ 로 값만 넘김': [('{"id": message_id, "body": body}', '{"id": str.__str__(message_id), "body": str.__str__(body)}')],
    '[트랜잭션] BEGIN IMMEDIATE 뒤 파이썬 쪽에서 확인하고 넣음': [('        with conn:\n            conn.execute(_SCHEMA)\n            conn.execute(_INDEX)\n            conn.execute(_RECORD, {"id": message_id, "body": body})\n', '        conn.isolation_level = None\n        conn.execute(_SCHEMA)\n        conn.execute(_INDEX)\n        conn.execute("BEGIN IMMEDIATE")\n        try:\n            if conn.execute("SELECT 1 FROM deliveries WHERE message_id = ?", (message_id,)).fetchone() is None:\n                conn.execute("INSERT INTO deliveries (message_id, body) VALUES (?, ?)", (message_id, body))\n            conn.execute("COMMIT")\n        except BaseException:\n            conn.execute("ROLLBACK")\n            raise\n')],
    '[색인] 색인 없이 (안전 - 주장은 속도를 말하지 않는다)': [('            conn.execute(_INDEX)\n', '')],
    '[인코딩] 확인을 트랜잭션 안에서 (안전)': [('        if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":\n            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n        with conn:\n', '        with conn:\n            if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":\n                raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
