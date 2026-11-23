"""FRED API 수집. 오류 메시지에 API 키가 섞이지 않도록 URL을 노출하지 않는다."""
from __future__ import annotations

import pandas as pd
import requests

BASE = "https://api.stlouisfed.org/fred"
TIMEOUT = 20


class FredError(RuntimeError):
    pass


def _get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{BASE}/{path}", params={**params, "file_type": "json"}, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise FredError(f"FRED 연결 실패 ({type(e).__name__})") from None
    if r.status_code != 200:
        try:
            msg = r.json().get("error_message", "")
        except ValueError:
            msg = ""
        raise FredError(f"FRED 오류 {r.status_code} {msg}".strip())
    return r.json()


def fetch(series_id: str, api_key: str, start: str = "2000-01-01") -> tuple[pd.Series, str]:
    """(값 시리즈, 단위 문자열)을 돌려준다."""
    meta = _get("series", {"series_id": series_id, "api_key": api_key})
    units = meta["seriess"][0].get("units", "")
    data = _get("series/observations",
                {"series_id": series_id, "api_key": api_key, "observation_start": start})
    values = {
        pd.Timestamp(o["date"]): float(o["value"])
        for o in data["observations"]
        if o["value"] not in (".", "")
    }
    s = pd.Series(values, dtype=float, name=series_id).sort_index()
    if s.empty:
        raise FredError(f"{series_id}: 데이터 없음")
    return s, units
