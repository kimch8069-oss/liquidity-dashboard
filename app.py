"""미국·한국 유동성 대시보드 (Streamlit).  실행: streamlit run app.py"""
from __future__ import annotations

import datetime as dt

import streamlit as st

import charts as ch
import indicators as ind
from config import clean_key, get_key

st.set_page_config(page_title="유동성 대시보드", page_icon="💧", layout="wide")
KST = dt.timezone(dt.timedelta(hours=9))


def secret(name: str) -> str | None:
    try:
        v = clean_key(st.secrets.get(name))
        if v:
            return v
    except Exception:
        pass
    return get_key(name)


@st.cache_data(ttl=6 * 3600, show_spinner="최신 데이터를 불러오는 중…")
def load(fred_key: str | None, ecos_key: str | None):
    return ind.build(fred_key, ecos_key), dt.datetime.now(KST)


# ── 상단: 제목, 갱신 버튼 ──────────────────────────────────
st.title("💧 미국·한국 유동성 대시보드")

fred_key, ecos_key = secret("FRED_API_KEY"), secret("ECOS_API_KEY")
missing = [n for n, k in (("FRED_API_KEY", fred_key), ("ECOS_API_KEY", ecos_key)) if not k]
if missing:
    st.warning(f"API 키가 없습니다: {', '.join(missing)}. "
               "`.streamlit/secrets.toml` 파일(배포 시에는 Secrets 설정)에 입력하세요.")

col_btn, col_info = st.columns([1, 3], vertical_alignment="center")
if col_btn.button("🔄 갱신", type="primary", use_container_width=True):
    load.clear()
    st.rerun()

data, fetched_at = load(fred_key, ecos_key)
col_info.caption(f"마지막 갱신: {fetched_at:%Y-%m-%d %H:%M} (KST) · 6시간마다 자동 갱신, 버튼으로 즉시 갱신")

period = st.segmented_control("그래프 기간", list(ch.PERIODS), default="3년") or "3년"


def show(fig, key: str):
    st.plotly_chart(fig, config=ch.STATIC, key=key)


def hint(*keys: str):
    for k in keys:
        i = data[k]
        if i.hint:
            st.caption(f"💡 **{i.name}**: {i.hint}")


def need(*keys: str) -> bool:
    """필요한 지표가 모두 있으면 True, 없으면 실패 사유를 보여준다."""
    bad = [data[k] for k in keys if not data[k].ok]
    for i in bad:
        st.error(f"{i.name} 불러오기 실패: {i.error}")
    return not bad


def available(*keys: str) -> list[tuple[str, object]]:
    out = []
    for k in keys:
        i = data[k]
        if i.ok:
            out.append((i.name, i.s))
        else:
            st.error(f"{i.name} 불러오기 실패: {i.error}")
    return out


# ── 핵심 수치 카드 ────────────────────────────────────────
CARDS = ["us_m2", "kr_m2_new", "net_liq",
         "us_10y", "us_10y2y", "hy",
         "kr_3y", "kr_10y3y", "usdkrw"]


def card(i: ind.Indicator):
    with st.container(border=True):
        if not i.ok:
            st.markdown(f"**{i.name}**")
            st.caption(f"⚠️ 불러오기 실패: {i.error}")
            return
        st.metric(i.name, i.fmt(i.latest), delta=i.fmt_delta(),
                  delta_color=i.delta_color, help=i.hint or None)
        st.caption(f"기준일 {i.latest_date:%Y-%m-%d} · {i.source}")
        show(ch.sparkline(i.s), key=f"spark_{i.key}")


for row in range(0, len(CARDS), 3):
    for col, k in zip(st.columns(3), CARDS[row:row + 3]):
        with col:
            card(data[k])

# ── 탭 ────────────────────────────────────────────────────
tab_m, tab_r, tab_l, tab_k = st.tabs(["통화량", "금리", "유동성", "한국 수급"])

with tab_m:
    series = available("us_m2", "kr_m2_new", "kr_m2_old")
    if series:
        refs = []
        if data["us_m2"].ok:
            refs.append((data["us_m2"].s.mean(), f"미국 M2 장기평균 {data['us_m2'].s.mean():.1f}%"))
        show(ch.line(series, "M2 증가율 (전년 대비)", period, "%", refs=refs, decimals=1), "m2")
    hint("us_m2", "kr_m2_old")

with tab_r:
    us = available("us_2y", "us_10y")
    if us:
        show(ch.line(us, "미국 국채 금리", period, "%"), "us_rates")
    if need("us_10y2y"):
        show(ch.spread_bar("10Y−2Y", data["us_10y2y"].s, "미국 10년−2년 금리차 (빨강=역전)", period), "us_sp")
    hint("us_10y", "us_10y2y")

    kr = available("kr_3y", "kr_10y", "kr_base")
    if kr:
        show(ch.line(kr, "한국 국고채 금리와 기준금리", period, "%", decimals=3), "kr_rates")
    if need("kr_10y3y"):
        show(ch.spread_bar("10Y−3Y", data["kr_10y3y"].s, "한국 10년−3년 금리차 (빨강=역전)",
                           period, decimals=3), "kr_sp")
    if need("kr_3y_base"):
        show(ch.spread_bar("3Y−기준금리", data["kr_3y_base"].s, "국고 3년 − 기준금리", period,
                           decimals=3), "kr_3b")
    hint("kr_3y", "kr_10y3y", "kr_3y_base")

with tab_l:
    if need("net_liq", "sp500"):
        show(ch.dual(("연준 순유동성", data["net_liq"].s, "조 달러"),
                     ("S&P500", data["sp500"].s, "지수"),
                     "연준 순유동성 vs S&P500", period), "netliq")
    hint("net_liq")
    for k, title in (("hy", "하이일드 스프레드"), ("sofr_iorb", "SOFR − IORB (bp)"),
                     ("dollar", "달러지수 (Broad)"), ("usdkrw", "원/달러 환율")):
        if need(k):
            i = data[k]
            refs = [(0, "0")] if k == "sofr_iorb" else []
            show(ch.line([(i.name, i.s)], title, period, i.unit, refs=refs, decimals=i.decimals), k)
        hint(k)

with tab_k:
    if need("kospi"):
        show(ch.line([("KOSPI", data["kospi"].s)], "KOSPI", period, decimals=0), "kospi")
    st.info("📌 준비 중: 고객예탁금 · 신용융자 잔고 · MMF 잔고 · 외국인 순매수\n\n"
            "안정적인 공식 API를 확인한 뒤 KOSPI와 겹친 그래프로 추가할 예정입니다.")

st.divider()
st.caption("데이터: FRED (미국 세인트루이스 연준), 한국은행 ECOS. 투자 판단의 참고용이며 투자 권유가 아닙니다.")
