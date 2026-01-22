
import os
import pandas as pd
import numpy as np
import streamlit as st
import FinanceDataReader as fdr
import plotly.express as px
from streamlit_lightweight_charts import renderLightweightCharts
from datetime import timedelta

# =========================
# Page Config
# =========================
st.set_page_config(layout="wide", page_title="커뮤니티 → 주식 시장 반응 분석")

# =========================
# 데이터 경로 (UI 비노출)
# =========================
DATA_PATH = {
    "DCInside": {
        "삼성전자": "../zzimni/data/daily_outputs/삼성전자_일별집계_OI_2025-01-14_2026-01-14.csv",
        "SK하이닉스": "../zzimni/data/daily_outputs/하이닉스_일별집계_OI_2025-01-14_2026-01-14.csv",
    },
    "FmKorea": {
        "삼성전자": "../data/samsung_data.csv",
        "SK하이닉스": "../data/hynix_data.csv",
    }
}

# 공포–탐욕 지수 (커뮤니티별)
FNG_PATH = {
    "FmKorea": {
        "삼성전자": "../FmKorea/data/samsung_fng.csv",
        "SK하이닉스": "../FmKorea/data/hynix_fng.csv",
    },
    "DCInside": {
        "삼성전자": "../FmKorea/data/samsung_fng_dc.csv",
        "SK하이닉스": "../FmKorea/data/hynix_fng_dc.csv",
    }
}

STOCK_INFO = {
    "삼성전자": "005930",
    "SK하이닉스": "000660"
}

# =========================
# Sidebar UI
# =========================
st.sidebar.header("📊 분석 설정")

start = st.sidebar.date_input("시작일", pd.to_datetime("2025-01-14").date())
end   = st.sidebar.date_input("종료일",   pd.to_datetime("2026-01-14").date())

community = st.sidebar.selectbox("커뮤니티 선택", ["DCInside", "FmKorea"])
stock_name = st.sidebar.selectbox("주식 선택", ["삼성전자", "SK하이닉스"])

selected_metrics = st.sidebar.multiselect(
    "표시할 커뮤니티 지표",
    ["조회수", "게시글수", "댓글수", "좋아요수", "공포-탐욕지수"],
    default=["게시글수"]
)

stock_indicators = st.sidebar.multiselect(
    "표시할 주식 지표",
    ["주가", "거래량", "수익률"],
    default=["주가"]
)

# =========================
# 컬럼 매핑
# =========================
METRIC_COL = {
    "조회수": "조회수_z",
    "게시글수": "게시글수_z",
    "댓글수": "댓글수_z",
    "좋아요수": "좋아요수_z",
    "공포-탐욕지수": "공포-탐욕지수",
}

METRIC_COLOR = {
    "조회수": "rgba(140,86,75,0.6)",
    "게시글수": "rgba(50,50,50,0.6)",
    "댓글수": "rgba(44,160,140,0.6)",
    "좋아요수": "rgba(188,189,34,0.6)",
    "공포-탐욕지수": "rgba(214,39,40,0.6)",
}

# =========================
# Data Loaders
# =========================
@st.cache_data
def load_price(ticker, start, end):
    df = fdr.DataReader(ticker, str(start - timedelta(days=14)), str(end))
    return df.reset_index()

@st.cache_data
def load_community(path, start, end):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
    return df[(df["날짜"] >= start) & (df["날짜"] <= end)]

@st.cache_data
def load_fng(path, start, end):
    df = pd.read_csv(path)
    df["날짜"] = pd.to_datetime(df["date"]).dt.date
    df = df.rename(columns={"fng_index": "공포-탐욕지수"})
    return df[(df["날짜"] >= start) & (df["날짜"] <= end)]

# =========================
# Lightweight Chart Helpers
# =========================
def make_candle(df):
    return [{
        "time": d.strftime("%Y-%m-%d"),
        "open": float(o), "high": float(h),
        "low": float(l), "close": float(c)
    } for d,o,h,l,c in zip(df["Date"],df["Open"],df["High"],df["Low"],df["Close"])]

def make_volume(df):
    return [{"time": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d,v in zip(df["Date"], df["Volume"])]

def make_return(df):
    df = df.copy()
    df["Return"] = df["Close"].pct_change() * 100
    return [{"time": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d,v in zip(df["Date"], df["Return"]) if not np.isnan(v)]

def build_community_series(df):
    series = []

    for m in selected_metrics:
        col = METRIC_COL[m]
        if col not in df.columns:
            continue

        clean_df = df[["날짜", col]].dropna()

        if clean_df.empty:
            continue

        series.append({
            "type": "Line",
            "data": [
                {
                    "time": d.strftime("%Y-%m-%d"),
                    "value": float(v)
                }
                for d, v in zip(clean_df["날짜"], clean_df[col])
                if not np.isnan(v)
            ],
            "options": {
                "color": METRIC_COLOR[m],
                "lineWidth": 2,
                "priceScaleId": "left"
            }
        })

    return series


def render_lightweight(title, base_series, comm_series, key, right_label):
    st.subheader(title)
    renderLightweightCharts(
        [{
            "chart": {"height": 420},
            "series": base_series + comm_series
        }],
        key=key
    )
    st.caption(f"오른쪽 축: {right_label} / 왼쪽 축: 커뮤니티 지표")

# =========================
# Scatter Data Builder
# =========================
@st.cache_data
def build_scatter(comm_df, price_df, metric_col, target):
    price_df = price_df.copy()
    price_df["Date_Only"] = price_df["Date"].dt.date

    merged = pd.merge(
        comm_df,
        price_df[["Date_Only", "Close", "Volume"]],
        left_on="날짜",
        right_on="Date_Only",
        how="inner"
    )

    merged["Return"] = merged["Close"].pct_change() * 100

    if target == "거래량":
        merged["Target"] = merged["Volume"].shift(-1)
        ylabel = "차기 거래일 거래량"
    else:
        merged["Target"] = merged["Return"].shift(-1)
        ylabel = "차기 거래일 수익률 (%)"

    merged = merged.dropna(subset=[metric_col, "Target"])
    return merged, ylabel

# =========================
# Main
# =========================
ticker = STOCK_INFO[stock_name]
comm_path = DATA_PATH[community][stock_name]

price_df = load_price(ticker, start, end)
comm_df = load_community(comm_path, start, end)

# 공포–탐욕 지수 병합
if "공포-탐욕지수" in selected_metrics:
    fng_df = load_fng(FNG_PATH[community][stock_name], start, end)
    comm_df = pd.merge(
        comm_df,
        fng_df[["날짜", "공포-탐욕지수"]],
        on="날짜",
        how="left"
    )

st.title(f"{stock_name} | {community} 커뮤니티 → 시장 반응 분석")

# =========================
# 주식 지표별 렌더링
# =========================
for indicator in stock_indicators:

    st.divider()
    st.header(f"📌 {indicator} 기준 분석")

    if indicator == "주가":
        base = [{"type": "Candlestick", "data": make_candle(price_df)}]
    elif indicator == "거래량":
        base = [{"type": "Histogram", "data": make_volume(price_df)}]
    else:
        base = [{"type": "Line", "data": make_return(price_df),
                 "options": {"color": "rgba(31,119,180,0.9)", "lineWidth": 2}}]

    render_lightweight(
        f"{indicator} vs 커뮤니티 지표 (당일)",
        base,
        build_community_series(comm_df),
        f"lw_{indicator}_{community}_{stock_name}",
        indicator
    )

    # --- 산점도 ---
    st.subheader(f"📊 커뮤니티 → 다음 거래일 {indicator}")
    for m in selected_metrics:
        if m not in comm_df.columns:
            continue

        df_scatter, ylabel = build_scatter(
            comm_df,
            price_df,
            METRIC_COL[m],
            indicator
        )

        corr = df_scatter[METRIC_COL[m]].corr(df_scatter["Target"])

        fig = px.scatter(
            df_scatter,
            x=METRIC_COL[m],
            y="Target",
            trendline="ols",
            color="Target",
            color_continuous_scale="RdYlGn",
            labels={
                METRIC_COL[m]: m,
                "Target": ylabel
            },
            hover_data=["날짜"]
        )

        fig.update_layout(height=480)
        chart_key = f"scatter_{community}_{stock_name}_{indicator}_{m}"
        st.plotly_chart(fig, use_container_width=True, key=chart_key)
        st.info(f"📈 {m} 상관계수: {corr:.3f}")
