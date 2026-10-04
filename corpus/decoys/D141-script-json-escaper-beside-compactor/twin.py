"""초기 상태를 script 에 싣기 - 두 JSON 도우미 중 HTML 에 넣는 쪽만 < · > · & 를 이스케이프한다."""

import json


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def _script_json(value: object) -> str:
    text = json.dumps(value, separators=(",", ":"), allow_nan=False)
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def page(state: object) -> str:
    return f'<script type="application/json" id="state">{_compact_json(state)}</script>'
