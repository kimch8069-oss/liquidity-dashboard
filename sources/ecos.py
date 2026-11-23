"""한국은행 ECOS Open API 수집. 키가 URL 경로에 들어가므로 오류 메시지에 URL을 넣지 않는다."""
from __future__ import annotations

import datetime as dt
import threading
import time

import pandas as pd
import requests

BASE = "https://ecos.bok.or.kr/api"
TIMEOUT = (5, 15)      # (연결, 응답) 초. ECOS는 가끔 응답이 멈추므로 짧게 끊고 다시 시도한다.
RETRIES = 4
CHUNK_YEARS = 3        # 일별 데이터는 3년씩 나눠 받는다 (큰 요청일수록 느리고 끊김이 잦음)
_LIMIT = threading.Semaphore(3)  # 동시에 너무 많이 보내면 ECOS가 오류를 돌려준다
NO_RETRY = {"INFO-200", "INFO-100", "ERROR-300", "ERROR-301"}  # 데이터 없음, 인증키 오류 등


class EcosError(RuntimeError):
    pass


def _call(api_key: str, service: str, *parts: str, start: int = 1, end: int = 100000) -> list[dict]:
    path = "/".join([BASE, service, api_key, "json", "kr", str(start), str(end), *parts])
    err = "알 수 없음"
    for attempt in range(RETRIES):
        if attempt:
            time.sleep(attempt)
        try:
            with _LIMIT:
                r = requests.get(path, timeout=TIMEOUT)
        except requests.RequestException as e:
            err = f"연결 실패 ({type(e).__name__})"
            continue
        if r.status_code != 200:
            err = f"HTTP 오류 {r.status_code}"
            continue
        body = r.json()
        if "RESULT" not in body:
            return body.get(service, {}).get("row", [])
        code, msg = body["RESULT"].get("CODE", ""), body["RESULT"].get("MESSAGE", "")
        err = f"{code}: {msg.splitlines()[0] if msg else ''}"
        if code in NO_RETRY:  # 데이터 없음·인증키 오류는 다시 시도해도 같다
            break
    raise EcosError(f"ECOS {err} ({attempt + 1}회 시도)")


def _fmt(d: dt.date, cycle: str) -> str:
    return d.strftime("%Y%m%d") if cycle == "D" else d.strftime("%Y%m")


def _parse(t: str, cycle: str) -> pd.Timestamp:
    if cycle == "D":
        return pd.Timestamp(dt.datetime.strptime(t, "%Y%m%d"))
    # 월 데이터는 해당 월 말일로 둔다
    return pd.Timestamp(dt.datetime.strptime(t, "%Y%m")) + pd.offsets.MonthEnd(0)


def _windows(start: dt.date, cycle: str) -> list[tuple[str, str]]:
    today = dt.date.today()
    if cycle != "D":
        return [(_fmt(start, cycle), _fmt(today, cycle))]
    out, y = [], start.year
    while y <= today.year:
        a = max(start, dt.date(y, 1, 1))
        b = min(today, dt.date(y + CHUNK_YEARS - 1, 12, 31))
        out.append((_fmt(a, cycle), _fmt(b, cycle)))
        y += CHUNK_YEARS
    return out


def fetch(spec: dict, api_key: str, start: str = "2000-01-01") -> pd.Series:
    cycle = spec["cycle"]
    rows = []
    for begin, finish in _windows(dt.date.fromisoformat(start), cycle):
        try:
            rows += _call(api_key, "StatisticSearch", spec["stat"], cycle, begin, finish, *spec["items"])
        except EcosError as e:
            if "INFO-200" not in str(e):  # 해당 구간에 데이터 없음은 건너뛴다
                raise
    values = {}
    for row in rows:
        v = row.get("DATA_VALUE")
        if v in (None, "", "-"):
            continue
        values[_parse(row["TIME"], cycle)] = float(str(v).replace(",", ""))
    s = pd.Series(values, dtype=float).sort_index()
    if s.empty:
        raise EcosError("데이터 없음")
    return s


def table_list(api_key: str) -> list[dict]:
    return _call(api_key, "StatisticTableList", end=10000)


def item_list(api_key: str, stat: str) -> list[dict]:
    return _call(api_key, "StatisticItemList", stat, end=2000)
