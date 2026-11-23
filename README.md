# 💧 미국·한국 유동성 대시보드

M2 통화량, 국채금리, 연준 순유동성, 신용 스프레드, 환율, 주가지수를 한 화면에서 보는 Streamlit 대시보드입니다.
[갱신] 버튼을 누르면 FRED와 한국은행 ECOS에서 최신 데이터를 다시 받아옵니다(약 20초). 평소에는 6시간 동안 캐시를 씁니다.

## 실행 방법 (노트북)

1. 패키지 설치
   ```
   pip install -r requirements.txt
   ```
2. `.streamlit/secrets.toml`에 API 키 입력 (이 파일은 GitHub에 올리지 않습니다)
   ```
   FRED_API_KEY = "발급받은 키"
   ECOS_API_KEY = "발급받은 키"
   ```
3. 실행
   ```
   streamlit run app.py
   ```
   같은 와이파이의 휴대폰에서 보려면 `--server.address 0.0.0.0`을 붙이고, 휴대폰에서 `http://노트북IP:8501`로 접속합니다.

## 도구

| 명령 | 용도 |
|---|---|
| `python check_data.py` | 모든 지표의 최신값을 터미널에 출력 (검증용) |
| `python verify_ecos.py` | ECOS 통계 코드가 실제 어떤 항목인지 확인 |

## 지표와 출처

| 구분 | 지표 | 출처 (코드) |
|---|---|---|
| 통화량 | 미국 M2 증가율(YoY) | FRED `M2SL` |
| | 한국 M2 증가율 신 기준 / 구 기준(수익증권 포함) | ECOS `161Y006` / `BBHA00`, `BBHA16` |
| 미국 금리 | 국채 2년, 10년, 10년−2년 금리차 | FRED `DGS2`, `DGS10`, `T10Y2Y` |
| 한국 금리 | 기준금리 | ECOS `722Y001` / `0101000` |
| | 국고채 2년, 3년, 10년 | ECOS `817Y002` / `010195000`, `010200000`, `010210000` |
| | 10년−3년, 3년−기준금리 | 계산 |
| 유동성 | 연준 순유동성 = 총자산 − TGA − 역레포 | FRED `WALCL`, `WTREGEN`, `RRPONTSYD` |
| | SOFR − IORB | FRED `SOFR`, `IORB` |
| | 하이일드 스프레드 | FRED `BAMLH0A0HYM2` |
| | 달러지수(Broad) | FRED `DTWEXBGS` |
| | 원/달러 환율 | ECOS `731Y001` / `0000001` |
| 주가지수 | S&P500, KOSPI | FRED `SP500`, ECOS `802Y001` / `0001000` |

## 파일 구조

```
app.py            화면 (카드, 탭, 갱신 버튼)
indicators.py     지표 계산
charts.py         plotly 그래프
config.py         지표 목록, API 키 로딩
sources/fred.py   FRED 수집
sources/ecos.py   ECOS 수집 (3년 단위 분할, 자동 재시도)
```

## 참고

- 한국은행 ECOS는 가끔 응답이 느리거나 끊깁니다. 자동으로 다시 시도하며, 그래도 실패한 지표만 '불러오기 실패'로 표시됩니다.
- FRED 미국 금리는 하루 늦게 반영될 수 있습니다.
- 준비 중: 고객예탁금, 신용융자 잔고, MMF 잔고, 외국인 순매수.
- 투자 판단의 참고용이며 투자 권유가 아닙니다.
