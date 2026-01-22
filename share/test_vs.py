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

FG_CSV_PATH = st.sidebar.text_input(
    "FM코리아 공포-탐욕 CSV 경로",
    value="../FmKorea/output/daily_fg_index.csv"
)

# =========================
# 종목 설정
# =========================
STOCKS = {
    "삼성전자": "005930",
    "하이닉스": "000660",
}

stock_name = st.sidebar.selectbox("종목 선택", list(STOCKS.keys()))
ticker = STOCKS[stock_name]

# =========================
# Data Load
# =========================
@st.cache_data
def load_price(ticker, start, end):
    df = fdr.DataReader(ticker, str(start), str(end)).reset_index()
    return df

@st.cache_data
def load_fg_csv(path, start, end):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    return df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

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
    } for d,o,h,l,c in zip(df["Date"], df["Open"], df["High"], df["Low"], df["Close"])]

def make_volume(df):
    return [{
        "time": d.strftime("%Y-%m-%d"),
        "value": float(v),
    } for d,v in zip(df["Date"], df["Volume"])]

def make_fg_series(df):
    return [{
        "time": d.strftime("%Y-%m-%d"),
        "value": float(v),
    } for d,v in zip(df["date"], df["fg_index"])]

def render_chart(title, base_series, fg_series, key, right_label):
    chart = {
        "height": 480,
        "layout": {
            "background": {"type": "solid", "color": "white"},
            "textColor": "black"
        },
        "rightPriceScale": {"borderVisible": True},
        "leftPriceScale": {"visible": True},
        "grid": {
            "vertLines": {"color": "rgba(200,200,200,0.3)"},
            "horzLines": {"color": "rgba(200,200,200,0.3)"},
        },
    }

    st.subheader(title)
    renderLightweightCharts(
        [{
            "chart": chart,
            "series": base_series + fg_series
        }],
        key=key
    )
    st.caption(f"오른쪽 축: {right_label} / 왼쪽 축: 공포–탐욕 지수")

# =========================
# Run
# =========================
price_df = load_price(ticker, start, end)
fg_df = load_fg_csv(FG_CSV_PATH, start, end)

st.title(f"{stock_name} 주가 · 거래량 vs 공포–탐욕 지수")

# =========================
# 주가 기준
# =========================
if compare_mode == "주가":
    candles = make_candles(price_df)

    base_price_series = [{
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
    }]

    fg_series = [{
        "type": "Line",
        "data": make_fg_series(fg_df),
        "options": {
            "color": "rgba(44,160,44,0.8)",
            "lineWidth": 2,
            "priceScaleId": "left",
        },
    }]

    render_chart(
        "주가 vs 공포–탐욕 지수",
        base_price_series,
        fg_series,
        "price_fg",
        "주가(원)"
    )

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

    fg_series = [{
        "type": "Line",
        "data": make_fg_series(fg_df),
        "options": {
            "color": "rgba(214,39,40,0.8)",
            "lineWidth": 2,
            "priceScaleId": "left",
        },
    }]

    render_chart(
        "거래량 vs 공포–탐욕 지수",
        base_volume_series,
        fg_series,
        "volume_fg",
        "거래량"
    )
