"""상태 점검 - 요청 주소는 고정된 지역 표에서만 나온다."""

import urllib.error
import urllib.request

_STATUS_URLS = {
    "kr": "https://kr.status.example.com/health",
    "jp": "https://jp.status.example.com/health",
    "us": "https://us.status.example.com/health",
}


def _status_url(region: str) -> str:
    return f"https://{region}.status.example.com/health"


def check(region: str) -> int:
    try:
        with urllib.request.urlopen(_status_url(region), timeout=3) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code
