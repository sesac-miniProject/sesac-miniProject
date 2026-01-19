import streamlit as st
import FinanceDataReader as fdr
from streamlit_lightweight_charts import renderLightweightCharts

df = fdr.DataReader("005930", "2025-01-14", "2026-01-14").reset_index()

# 1) candles 데이터는 time/open/high/low/close만
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

# 2) 차트 옵션(TradingView LWCharts 옵션)으로 y축 여백 조정
chart_options = {
    "height": 500,
    "rightPriceScale": {
        "scaleMargins": {"top": 0.1, "bottom": 0.0},  # 아래 여백 0
        "borderVisible": True,
        "autoScale": True,
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
    }
]

st.title("005930 TradingView-like Chart")
renderLightweightCharts([{"chart": chart_options, "series": series}], key="005930")
