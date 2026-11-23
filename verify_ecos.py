"""ECOS 통계 코드 확인용.  실행: python verify_ecos.py
1) config.py 에 적힌 코드가 실제로 어떤 항목인지 이름을 출력
2) M2·금리·환율 관련 통계표를 키워드로 찾아 출력 (M2 코드 채우기용)
"""
from __future__ import annotations

import sys

import config
from sources import ecos

KEYWORDS = ["M2", "광의통화", "통화 및 유동성"]


def main():
    key = config.get_key("ECOS_API_KEY")
    if not key:
        sys.exit("ECOS_API_KEY 가 없습니다. .streamlit/secrets.toml 에 입력하세요.")

    print("== 설정된 코드 확인 ==")
    for k, spec in config.ECOS_SERIES.items():
        if not spec["stat"]:
            print(f"[{k}] 코드 미설정")
            continue
        try:
            items = ecos.item_list(key, spec["stat"])
        except Exception as e:
            print(f"[{k}] {spec['stat']} 조회 실패: {e}")
            continue
        hit = [r for r in items if r["ITEM_CODE"] == spec["items"][0] and r["CYCLE"] == spec["cycle"]]
        if hit:
            r = hit[0]
            print(f"[{k}] OK  {r['STAT_NAME']} / {r['ITEM_NAME']} ({r['CYCLE']}, {r['START_TIME']}~{r['END_TIME']})")
        else:
            print(f"[{k}] 항목 코드 불일치. 이 통계표의 항목:")
            for r in items[:30]:
                print(f"     {r['ITEM_CODE']}  {r['ITEM_NAME']}  ({r['CYCLE']})")

    print("\n== M2 관련 통계표 ==")
    for r in ecos.table_list(key):
        if any(w in r.get("STAT_NAME", "") for w in KEYWORDS) and r.get("STAT_CODE"):
            print(f"{r['STAT_CODE']}  {r['STAT_NAME']}  ({r.get('CYCLE') or '-'})")


if __name__ == "__main__":
    main()
