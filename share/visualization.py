import os
import pandas as pd
import streamlit as st
import FinanceDataReader as fdr
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(layout="wide")

# =========================
# Sidebar
# =========================
st.sidebar.header("설정")

start = st.sidebar.date_input("시작일", pd.to_datetime("2025-01-14").date())
end   = st.sidebar.date_input("종료일",   pd.to_datetime("2026-01-14").date())

compare_mode = st.sidebar.selectbox(
    "비교 기준 선택",
    ["주가", "거래량"]
)

DC_DIR = st.sidebar.text_input(
    "DCInside CSV 경로",
    value="../zzimni/data/daily_outputs"
)

FM_DIR = st.sidebar.text_input(
    "FM코리아 CSV 경로",
    value="../data"
)

# =========================
# 종목 설정
# =========================
STOCKS = {
    "삼성전자": {
        "ticker": "005930",
        "dc_csv": "삼성전자_일별집계_OI_2025-01-14_2026-01-14.csv",
        "fm_csv": "samsung_data.csv",
    },
    "하이닉스": {
        "ticker": "000660",
        "dc_csv": "하이닉스_일별집계_OI_2025-01-14_2026-01-14.csv",
        "fm_csv": "hynix_data.csv",
    },
}

stock_name = st.sidebar.selectbox("종목 선택", list(STOCKS.keys()))

METRICS = {
    "과열지수(OI)": "과열지수_OI",
    "조회수": "조회수",
    "게시글수": "게시글수",
    "댓글수": "댓글수",
    "좋아요수": "좋아요수",
}

COLOR_MAP = {
    "과열지수(OI)": "rgba(50,50,50,0.7)",
    "조회수": "rgba(140,86,75,0.5)",
    "게시글수": "rgba(214, 97, 77, 0.5)",
    "댓글수": "rgba(44,160,140,0.5)",
    "좋아요수": "rgba(188,189,34,0.5)",
}

selected_metrics = st.sidebar.multiselect(
    "표시할 커뮤니티 지표",
    list(METRICS.keys()),
    default=["과열지수(OI)"]
)

# =========================
# Data Load
# =========================
@st.cache_data
def load_price(ticker, start, end):
    return fdr.DataReader(ticker, str(start), str(end)).reset_index()

@st.cache_data
def load_csv(path, start, end):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df[(df["날짜"].dt.date >= start) & (df["날짜"].dt.date <= end)]

# =========================
# Series Builders
# =========================
def make_candles(df):
    return [{
        "time": d.strftime("%Y-%m-%d"),
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
    } for d,o,h,l,c in zip(df["Date"],df["Open"],df["High"],df["Low"],df["Close"])]

def make_volume(df):
    return [{
        "time": d.strftime("%Y-%m-%d"),
        "value": float(v),
    } for d,v in zip(df["Date"], df["Volume"])]

def build_oi_series(df):
    series = []
    for m in selected_metrics:
        col = METRICS[m]
        line = [
            {"time": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d,v in zip(df["날짜"], df[col])
        ]
        series.append({
            "type": "Line",
            "data": line,
            "options": {
                "color": COLOR_MAP[m],
                "lineWidth": 2,
                "priceScaleId": "left",
            },
        })
    return series

def render_chart(title, base_series, oi_series, key, right_label):
    chart = {
        "height": 480,
        "layout": {"background": {"type": "solid", "color": "white"}, "textColor": "black"},
        "rightPriceScale": {"borderVisible": True},
        "leftPriceScale": {"visible": True},
        "grid": {
            "vertLines": {"color": "rgba(200,200,200,0.3)"},
            "horzLines": {"color": "rgba(200,200,200,0.3)"},
        },
    }

    st.subheader(title)
    renderLightweightCharts(
        [{"chart": chart, "series": base_series + oi_series}],
        key=key
    )
    st.caption(f"오른쪽 축: {right_label} / 왼쪽 축: 커뮤니티 지표")

# =========================
# Run
# =========================
stock = STOCKS[stock_name]

price_df = load_price(stock["ticker"], start, end)
dc_df = load_csv(os.path.join(DC_DIR, stock["dc_csv"]), start, end)
fm_df = load_csv(os.path.join(FM_DIR, stock["fm_csv"]), start, end)

st.title(f"{stock_name} 커뮤니티 비교 ({compare_mode} 기준)")

# =========================
# 주가 기준
# =========================
if compare_mode == "주가":
    candles = make_candles(price_df)

    base_price_series = [{
        "type": "Candlestick",
        "data": candles,
        "options": {
            "upColor": "red", "downColor": "blue",
            "borderUpColor": "red", "borderDownColor": "blue",
            "wickUpColor": "red", "wickDownColor": "blue",
        },
    }]

    render_chart("① DCInside + 주가", base_price_series, build_oi_series(dc_df), "dc_price", "주가(원)")
    st.divider()
    render_chart("② FM코리아 + 주가", base_price_series, build_oi_series(fm_df), "fm_price", "주가(원)")

# =========================
# 거래량 기준
# =========================
else:
    volume = make_volume(price_df)

    base_volume_series = [{
        "type": "Histogram",
        "data": volume,
        "options": {
            "color": "rgba(120,120,200,0.5)",
            "priceScaleId": "right",
        },
    }]

    render_chart("① DCInside + 거래량", base_volume_series, build_oi_series(dc_df), "dc_volume", "거래량")
    st.divider()
    render_chart("② FM코리아 + 거래량", base_volume_series, build_oi_series(fm_df), "fm_volume", "거래량")
