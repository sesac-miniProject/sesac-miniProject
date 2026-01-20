import os
import pandas as pd
import streamlit as st
import FinanceDataReader as fdr
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(layout="wide")

# =========================
# Sidebar: 설정
# =========================
st.sidebar.header("설정")

start = st.sidebar.date_input("시작일", value=pd.to_datetime("2025-01-14").date())
end   = st.sidebar.date_input("종료일", value=pd.to_datetime("2026-01-14").date())

oi_dir = st.sidebar.text_input(
    "OI CSV 폴더(daily_outputs)",
    value=r"C:\Users\Jeon\sesac-miniProject\완료\daily_outputs"
)

# 파일명은 네 저장 규칙 그대로 입력 (기본값도 그 규칙으로 생성)
samsung_oi_filename = st.sidebar.text_input(
    "삼성 OI CSV 파일명",
    value=f"삼성_일별집계_OI포함_{start}_{end}.csv"
)
hynix_oi_filename = st.sidebar.text_input(
    "하이닉스 OI CSV 파일명",
    value=f"하이닉스_일별집계_OI포함_{start}_{end}.csv"
)

samsung_oi_path = os.path.join(oi_dir, samsung_oi_filename)
hynix_oi_path = os.path.join(oi_dir, hynix_oi_filename)

# =========================
# 공통 함수: 캔들/라인 데이터 생성
# =========================
def make_candles(ticker: str, start_date, end_date):
    df = fdr.DataReader(ticker, str(start_date), str(end_date)).reset_index()
    candles = [
        {
            "time": d.strftime("%Y-%m-%d"),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
        }
        for d, o, h, l, c in zip(df["Date"], df["Open"], df["High"], df["Low"], df["Close"])
    ]
    return candles

def make_oi_line(csv_path: str, start_date, end_date):
    oi = pd.read_csv(csv_path, encoding="utf-8-sig")
    oi["날짜"] = pd.to_datetime(oi["날짜"])
    oi = oi[(oi["날짜"].dt.date >= start_date) & (oi["날짜"].dt.date <= end_date)].sort_values("날짜")

    line = [{"time": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d, v in zip(oi["날짜"], oi["과열지수_OI"])]
    return line

def render_price_with_oi(title: str, candles, oi_line, key: str, oi_color: str):
    chart_options = {
        "height": 520,

        # 오른쪽: 가격
        "rightPriceScale": {
            "borderVisible": True,
            "autoScale": True,
            "scaleMargins": {"top": 0.10, "bottom": 0.05},
        },

        # 왼쪽: OI
        "leftPriceScale": {
            "visible": True,
            "borderVisible": True,
            "autoScale": True,
            "scaleMargins": {"top": 0.10, "bottom": 0.05},
        },

        "layout": {
            "background": {"type": "solid", "color": "white"},
            "textColor": "black",
        },
        "grid": {
            "vertLines": {"color": "rgba(197, 203, 206, 0.3)"},
            "horzLines": {"color": "rgba(197, 203, 206, 0.3)"},
        },
    }

    series = [
        {
            "type": "Candlestick",
            "data": candles,
            "options": {
                "upColor": "red",
                "downColor": "blue",
                "borderUpColor": "red",
                "borderDownColor": "blue",
                "wickUpColor": "red",
                "wickDownColor": "blue",
            },
        },
        {
            "type": "Line",
            "data": oi_line,
            "options": {
                "color": oi_color,
                "lineWidth": 2,
                "priceScaleId": "left",   # ✅ OI는 왼쪽 스케일에 붙임 [web:287][web:296]
            },
        },
    ]

    st.subheader(title)
    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)
    st.caption("오른쪽 축: 가격(원), 왼쪽 축: 과열지수(OI).")

# =========================
# 입력 파일 체크
# =========================
if not os.path.exists(samsung_oi_path):
    st.error(f"삼성 OI CSV를 못 찾음: {samsung_oi_path}")
    st.stop()

if not os.path.exists(hynix_oi_path):
    st.error(f"하이닉스 OI CSV를 못 찾음: {hynix_oi_path}")
    st.stop()

# =========================
# 1) 위: 삼성(005930) + 삼성 OI
# =========================
samsung_candles = make_candles("005930", start, end)
samsung_oi_line = make_oi_line(samsung_oi_path, start, end)

render_price_with_oi(
    title="삼성전자(005930) 캔들 + 삼성 OI",
    candles=samsung_candles,
    oi_line=samsung_oi_line,
    key="chart_samsung",
    oi_color="#FF9900",
)

st.divider()

# =========================
# 2) 아래: 하이닉스(000660) + 하이닉스 OI
# =========================
hynix_candles = make_candles("000660", start, end)  # 000660 = SK하이닉스 예시 [web:309]
hynix_oi_line = make_oi_line(hynix_oi_path, start, end)

render_price_with_oi(
    title="SK하이닉스(000660) 캔들 + 하이닉스 OI",
    candles=hynix_candles,
    oi_line=hynix_oi_line,
    key="chart_hynix",
    oi_color="#2E86DE",
)
