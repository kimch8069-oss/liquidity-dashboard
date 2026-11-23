"""지표 정의와 API 키 로딩."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
PLACEHOLDER = "여기에"  # secrets.toml 예시 값에 들어 있는 문구

# 그래프 '전체' 기간용 수집 시작일
START_DATE = "2000-01-01"


def clean_key(value) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    if not value or PLACEHOLDER in value:
        return None
    return value


def get_key(name: str) -> str | None:
    """환경변수 → .streamlit/secrets.toml 순서로 API 키를 찾는다."""
    v = clean_key(os.environ.get(name))
    if v:
        return v
    path = ROOT / ".streamlit" / "secrets.toml"
    if path.exists():
        with open(path, "rb") as f:
            return clean_key(tomllib.load(f).get(name))
    return None


# ── FRED 시리즈 ─────────────────────────────────────────────
FRED_SERIES = [
    "M2SL",          # 미국 M2 (월, 계절조정)
    "DGS2",          # 미 국채 2년
    "DGS10",         # 미 국채 10년
    "T10Y2Y",        # 10년-2년 금리차
    "WALCL",         # 연준 총자산 (주간)
    "WTREGEN",       # 재무부 일반계정 TGA (주간)
    "RRPONTSYD",     # 역레포 잔액 (일간)
    "SOFR",          # 담보부 익일물 금리
    "IORB",          # 지급준비금 이자율
    "BAMLH0A0HYM2",  # 하이일드 스프레드
    "DTWEXBGS",      # 달러 지수 (Broad)
    "SP500",         # S&P500
]

# ── 한국은행 ECOS 통계 ──────────────────────────────────────
# stat: 통계표 코드, cycle: D(일)/M(월), items: 항목 코드 목록
# ※ verify_ecos.py 로 이름을 확인한 뒤 사용한다. stat=None 이면 '코드 확인 필요'.
ECOS_SERIES = {
    "kr_base":   dict(name="한국은행 기준금리", stat="722Y001", cycle="D", items=["0101000"]),
    "kr_2y":     dict(name="국고채 2년",       stat="817Y002", cycle="D", items=["010195000"]),
    "kr_3y":     dict(name="국고채 3년",       stat="817Y002", cycle="D", items=["010200000"]),
    "kr_10y":    dict(name="국고채 10년",      stat="817Y002", cycle="D", items=["010210000"]),
    "kospi":     dict(name="KOSPI",            stat="802Y001", cycle="D", items=["0001000"]),
    "usdkrw":    dict(name="원/달러 환율",      stat="731Y001", cycle="D", items=["0000001"]),
    # 161Y006 = M2 상품별 구성내역(평잔, 원계열). BBHA16 은 '[참고] 구 M2'
    "kr_m2_new": dict(name="M2 신 기준 (평잔, 원계열)", stat="161Y006", cycle="M", items=["BBHA00"]),
    "kr_m2_old": dict(name="M2 구 기준 (수익증권 포함)", stat="161Y006", cycle="M", items=["BBHA16"]),
}
