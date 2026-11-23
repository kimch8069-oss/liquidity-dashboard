"""원자료를 받아 대시보드 지표로 계산한다. 지표 하나가 실패해도 나머지는 계속 만든다."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd

import config
from sources import ecos, fred


@dataclass
class Indicator:
    key: str
    name: str
    unit: str
    source: str
    hint: str = ""
    decimals: int = 2
    delta_unit: str | None = None
    delta_color: str = "normal"   # Streamlit metric: normal / inverse / off
    series: pd.Series | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.series is not None and not self.series.dropna().empty

    @property
    def s(self) -> pd.Series:
        return self.series.dropna()

    @property
    def latest(self) -> float:
        return float(self.s.iloc[-1])

    @property
    def latest_date(self) -> pd.Timestamp:
        return self.s.index[-1]

    @property
    def delta(self) -> float | None:
        s = self.s
        return float(s.iloc[-1] - s.iloc[-2]) if len(s) > 1 else None

    def fmt(self, v: float) -> str:
        return f"{v:,.{self.decimals}f} {self.unit}".strip()

    def fmt_delta(self) -> str | None:
        d = self.delta
        if d is None:
            return None
        unit = self.delta_unit if self.delta_unit is not None else self.unit
        return f"{d:+,.{self.decimals}f} {unit}".strip()


class _Missing(Exception):
    pass


def _fetch_raw(fred_key: str | None, ecos_key: str | None) -> dict:
    """{('fred', id): (series, units) | 오류문자열, ('ecos', key): series | 오류문자열}"""
    raw: dict = {}
    futures = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for sid in config.FRED_SERIES:
            if not fred_key:
                raw[("fred", sid)] = "FRED_API_KEY 미설정"
            else:
                futures[("fred", sid)] = ex.submit(fred.fetch, sid, fred_key, config.START_DATE)
        for key, spec in config.ECOS_SERIES.items():
            if not ecos_key:
                raw[("ecos", key)] = "ECOS_API_KEY 미설정"
            elif not spec["stat"]:
                raw[("ecos", key)] = "ECOS 통계 코드 확인 필요 (verify_ecos.py)"
            else:
                futures[("ecos", key)] = ex.submit(ecos.fetch, spec, ecos_key, config.START_DATE)
        for k, fut in futures.items():
            try:
                raw[k] = fut.result()
            except Exception as e:  # 오류 메시지만 보관 (키 노출 방지)
                raw[k] = str(e) or type(e).__name__
    return raw


def build(fred_key: str | None, ecos_key: str | None) -> dict[str, Indicator]:
    raw = _fetch_raw(fred_key, ecos_key)

    def f(sid: str) -> pd.Series:
        v = raw[("fred", sid)]
        if isinstance(v, str):
            raise _Missing(f"{sid}: {v}")
        return v[0]

    def f_billions(sid: str) -> pd.Series:
        s, units = f(sid), raw[("fred", sid)][1].lower()
        if "million" in units:
            return s / 1000
        if "trillion" in units:
            return s * 1000
        return s

    def e(key: str) -> pd.Series:
        v = raw[("ecos", key)]
        if isinstance(v, str):
            raise _Missing(f"{config.ECOS_SERIES[key]['name']}: {v}")
        return v

    def align(s: pd.Series, index: pd.Index) -> pd.Series:
        """다른 주기의 시리즈를 index 날짜에 맞춘다(직전 값으로 채움)."""
        return s.reindex(s.index.union(index)).ffill().reindex(index)

    out: dict[str, Indicator] = {}

    def add(key, name, unit, source, fn, **kw):
        ind = Indicator(key, name, unit, source, **kw)
        try:
            ind.series = fn().dropna()
            if ind.series.empty:
                ind.error = "데이터 없음"
        except _Missing as ex:
            ind.error = str(ex)
        except Exception as ex:
            ind.error = f"계산 오류: {ex}"
        out[key] = ind

    pct = dict(unit="%", delta_unit="%p")
    sp = dict(unit="%p", delta_unit="%p")  # 금리차

    # ── 통화량 ──
    add("us_m2", "미국 M2 증가율(YoY)", source="FRED M2SL",
        fn=lambda: f("M2SL").pct_change(12, fill_method=None) * 100,
        hint="증가율이 높아지면 시중에 돈이 늘어나는 국면 (위험자산에 우호적)", decimals=1, **pct)
    add("kr_m2_new", "한국 M2 증가율 신 기준(YoY)", source="한국은행 ECOS",
        fn=lambda: e("kr_m2_new").pct_change(12, fill_method=None) * 100,
        hint="2025년 개편 후 기준 (수익증권 제외)", decimals=1, **pct)
    add("kr_m2_old", "한국 M2 증가율 구 기준(YoY)", source="한국은행 ECOS",
        fn=lambda: e("kr_m2_old").pct_change(12, fill_method=None) * 100,
        hint="수익증권 포함. 신 기준보다 높으면 펀드·ETF로 돈이 몰리는 중", decimals=1, **pct)

    # ── 미국 금리 ──
    add("us_2y", "미 국채 2년", source="FRED DGS2", fn=lambda: f("DGS2"),
        hint="연준 정책금리 기대를 반영", delta_color="inverse", **pct)
    add("us_10y", "미 국채 10년", source="FRED DGS10", fn=lambda: f("DGS10"),
        hint="높을수록 주식 밸류에이션 부담", delta_color="inverse", **pct)
    add("us_10y2y", "미 10년−2년 금리차", source="FRED T10Y2Y", fn=lambda: f("T10Y2Y"),
        hint="0 아래(역전)는 경기침체 경고, 역전 해소 국면도 주의", **sp)

    # ── 한국 금리 ──
    add("kr_base", "한국은행 기준금리", source="한국은행 ECOS", fn=lambda: e("kr_base"), **pct)
    add("kr_2y", "국고채 2년", source="한국은행 ECOS", fn=lambda: e("kr_2y"),
        delta_color="inverse", decimals=3, **pct)
    add("kr_3y", "국고채 3년", source="한국은행 ECOS", fn=lambda: e("kr_3y"),
        hint="기준금리 인하·인상 기대를 가장 민감하게 반영", delta_color="inverse", decimals=3, **pct)
    add("kr_10y", "국고채 10년", source="한국은행 ECOS", fn=lambda: e("kr_10y"),
        delta_color="inverse", decimals=3, **pct)
    add("kr_10y3y", "국고 10년−3년 금리차", source="한국은행 ECOS (계산)",
        fn=lambda: e("kr_10y") - align(e("kr_3y"), e("kr_10y").index),
        hint="0 아래(역전)는 경기 둔화 우려", decimals=3, **sp)
    add("kr_3y_base", "국고 3년−기준금리", source="한국은행 ECOS (계산)",
        fn=lambda: e("kr_3y") - align(e("kr_base"), e("kr_3y").index),
        hint="마이너스 폭이 클수록 시장이 금리 인하를 더 많이 기대", decimals=3, **sp)

    # ── 유동성 ──
    def net_liquidity():
        walcl = f_billions("WALCL")
        tga = align(f_billions("WTREGEN"), walcl.index)
        rrp = align(f_billions("RRPONTSYD"), walcl.index).fillna(0)
        return (walcl - tga - rrp) / 1000  # 조 달러

    add("net_liq", "연준 순유동성", source="FRED WALCL−WTREGEN−RRPONTSYD", fn=net_liquidity,
        unit="조 달러", decimals=2,
        hint="연준 자산 − TGA − 역레포. 늘면 시장에 돈이 풀리는 방향 (미 증시와 동행 경향)")
    add("sofr_iorb", "SOFR−IORB 스프레드", source="FRED SOFR, IORB",
        fn=lambda: (f("SOFR") - align(f("IORB"), f("SOFR").index)) * 100,
        unit="bp", decimals=0, delta_color="inverse",
        hint="0 위로 커지면 단기자금시장에 돈이 부족하다는 신호")
    add("hy", "하이일드 스프레드", source="FRED BAMLH0A0HYM2", fn=lambda: f("BAMLH0A0HYM2"),
        delta_color="inverse", **pct,
        hint="오르면 위험회피(유동성 위축), 내리면 위험선호")
    add("dollar", "달러지수 (Broad)", source="FRED DTWEXBGS", fn=lambda: f("DTWEXBGS"),
        unit="", decimals=2, delta_color="inverse",
        hint="달러 강세는 글로벌 유동성 위축, 신흥국 증시에 부담")
    add("usdkrw", "원/달러 환율", source="한국은행 ECOS", fn=lambda: e("usdkrw"),
        unit="원", decimals=1, delta_color="inverse",
        hint="환율 상승(원화 약세)은 외국인 자금 이탈과 함께 나타나는 경우가 많음")

    # ── 주가지수 ──
    add("sp500", "S&P500", source="FRED SP500", fn=lambda: f("SP500"), unit="", decimals=0)
    add("kospi", "KOSPI", source="한국은행 ECOS", fn=lambda: e("kospi"), unit="", decimals=2)

    return out
