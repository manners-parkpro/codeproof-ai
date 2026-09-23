"""경로 결합 - 이웃한 두 함수 중 하나만 진짜다."""

from pathlib import Path

_ROOT = Path("/srv/uploads").resolve()


def sanitize_label(value: str) -> str:
    """표시용 공백 정리. 경로 검증이 아니다."""
    return value.strip()


def sanitize_path(value: str) -> Path:
    candidate = (_ROOT / value).resolve()
    return candidate


def open_upload(name: str) -> bytes:
    return sanitize_path(name).read_bytes()
