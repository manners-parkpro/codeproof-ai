"""설정 파일 해석 - 해석기 모듈 이름은 형식마다 정해 둔 글자 그대로만 돌려준다."""

import importlib


def _parser_module(fmt: str) -> str:
    match fmt:
        case "json":
            return "json"
        case "toml":
            return "tomllib"
    return fmt


def parse(fmt: str, text: str) -> object:
    name = _parser_module(fmt)
    parser = importlib.import_module(name)
    return parser.loads(text)
