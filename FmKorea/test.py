import os
import pandas as pd
import numpy as np
import streamlit as st
import FinanceDataReader as fdr
import plotly.express as px
from streamlit_lightweight_charts import renderLightweightCharts
from datetime import timedelta

st.set_page_config(layout="wide", page_title="주식 심리 및 상관관계 분석")

# 1. CSS 스타일 정의
st.markdown("""
    <style>
    [data-testid="stMetric"] { background-color: transparent !important; border: none !important; box-shadow: none !important; padding: 5px !important; }
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; }
    .status-box { font-size: 18px; font-weight: bold; margin-top: -5px; padding-left: 5px; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# 2. 데이터 로드 함수
# =========================
@st.cache_data
def get_fng_data(csv_path, start_date, end_date):
    if not os.path.exists(csv_path): return pd.DataFrame()
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df[(df["date"] >= start_date) & (df["date"] <= end_date)].sort_values("date")

@st.cache_data
def get_stock_df(ticker, start_date, end_date):
    fetch_start = start_date - timedelta(days=14)
    df = fdr.DataReader(ticker, str(fetch_start), str(end_date))
    df['Change_Pct'] = df['Close'].pct_change() * 100
    return df.reset_index()

# =========================
# 3. 사이드바 및 종목 설정
# =========================
st.sidebar.header("📊 분석 설정")
start = st.sidebar.date_input("시작일", value=pd.to_datetime("2025-01-14").date())
end = st.sidebar.date_input("종료일", value=pd.to_datetime("2026-01-14").date())

# 종목 선택 (메인 화면 상단에서 사이드바로 이동하여 관리 효율 증대)
target_stock = st.sidebar.selectbox("분석 종목 선택", ["삼성전자(005930)", "SK하이닉스(000660)"])

# [핵심 수정] 종목별 파일 매핑 로직
if "삼성" in target_stock:
    ticker = "005930"
    FNG_FILE = r"..\data\samsung_fng.csv"
else:
    ticker = "000660"
    FNG_FILE = r"..\data\hynix_fng.csv"

# =========================
# 4. 메인 화면 구성
# =========================
st.title(f"🎯 {target_stock} 심리-데이터 상관관계 분석")

# 선택된 종목에 맞는 데이터 로드
df_fng = get_fng_data(FNG_FILE, start, end)
df_stock = get_stock_df(ticker, start, end)

if not df_fng.empty and not df_stock.empty:
    # --- [섹션 1] 날짜별 상세 분석 ---
    st.subheader("📅 특정 날짜 심리-주가 분석")
    selected_date = st.date_input("날짜 선택", value=df_fng["date"].iloc[-1])
    
    day_fng_row = df_fng[df_fng["date"] == selected_date]
    stock_current = df_stock[df_stock['Date'].dt.date == selected_date]

    if not day_fng_row.empty and not stock_current.empty:
        fng_sorted = df_fng.sort_values("date").reset_index()
        curr_idx = fng_sorted[fng_sorted["date"] == selected_date].index[0]
        fval = day_fng_row.iloc[0]['fng_index']
        f_delta = round(fval - fng_sorted.iloc[curr_idx-1]['fng_index'], 2) if curr_idx > 0 else 0

        s_idx = stock_current.index[0]
        day_prev = df_stock.iloc[s_idx-1] if s_idx > 0 else None
        day_now = df_stock.iloc[s_idx]
        day_next = df_stock.iloc[s_idx+1] if s_idx < len(df_stock)-1 else None

        if fval >= 60: state, s_color = "탐욕 (Greed)", "#008000"
        elif fval <= 40: state, s_color = "#FF4B4B", "#FF4B4B"
        else: state, s_color = "중립 (Neutral)", "gray"

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(label=f"[{selected_date}] 지수", value=f"{fval} pts", delta=f"{f_delta}")
            st.markdown(f"<div class='status-box'>상태: <span style='color:{s_color}'>{state}</span></div>", unsafe_allow_html=True)
        with m2:
            if day_prev is not None: st.metric("전날 주가 변동", f"{day_prev['Close']:,}원", f"{day_prev['Change_Pct']:.2f}%")
        with m3: st.metric("당일 주가 변동", f"{day_now['Close']:,}원", f"{day_now['Change_Pct']:.2f}%")
        with m4:
            if day_next is not None: st.metric("다음날 주가 변동", f"{day_next['Close']:,}원", f"{day_next['Change_Pct']:.2f}%")

    st.divider()

    # --- [섹션 2] 시계열 추세 분석 ---
    st.subheader("📈 시계열 추세")
    candles = [{"time": d.strftime("%Y-%m-%d"), "open": float(o), "high": float(h), "low": float(l), "close": float(c)} 
               for d, o, h, l, c in zip(df_stock["Date"], df_stock["Open"], df_stock["High"], df_stock["Low"], df_stock["Close"])
               if start <= d.date() <= end]
    fng_line = [{"time": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df_fng["date"], df_fng["fng_index"])]
    density_bar = [{"time": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df_fng["date"], df_fng["emotion_density"])]

    renderLightweightCharts([{"chart": {"height": 350}, "series": [{"type": "Candlestick", "data": candles, "options": {"upColor": "red", "downColor": "blue"}}]}], key=f"p_chart_{ticker}")
    fng_series = [
        {"type": "Histogram", "data": density_bar, "options": {"color": "rgba(33, 150, 243, 0.2)", "priceScaleId": "left"}},
        {"type": "Line", "data": fng_line, "options": {"color": "#AB47BC", "lineWidth": 3, "priceScaleId": "left", "title": "F&G Index"}}
    ]
    renderLightweightCharts([{"chart": {"height": 250, "leftPriceScale": {"visible": True}}, "series": fng_series}], key=f"f_chart_{ticker}")

    st.divider()

    # --- [섹션 3] 상관관계 산점도 분석 (자동 업데이트) ---
    st.subheader(f"📊 {target_stock} 심리 vs 수익률 상관관계")
    
    df_stock_copy = df_stock.copy()
    df_stock_copy['Date_Only'] = pd.to_datetime(df_stock_copy['Date']).dt.date
    df_stock_copy['Next_Day_Return'] = df_stock_copy['Change_Pct'].shift(-1)
    
    merged = pd.merge(df_fng, df_stock_copy[['Date_Only', 'Next_Day_Return']], left_on='date', right_on='Date_Only').dropna()
    
    if not merged.empty:
        fig = px.scatter(
            merged, x="fng_index", y="Next_Day_Return",
            size="emotion_density", color="Next_Day_Return",
            color_continuous_scale="RdYlGn",
            labels={"fng_index": "공포·탐욕 지수", "Next_Day_Return": "다음날 수익률 (%)"},
            hover_data=["date"], trendline="ols"
        )
        fig.update_layout(plot_bgcolor="white", height=500)
        st.plotly_chart(fig, use_container_width=True)

        corr = merged['fng_index'].corr(merged['Next_Day_Return'])
        st.write(f"💡 **상관계수:** `{corr:.3f}`")
        st.info(f"선택된 파일: `{os.path.basename(FNG_FILE)}`을 분석 중입니다.")
    else:
        st.warning("상관관계를 분석할 병합 데이터가 없습니다.")

else:
    st.error(f"데이터를 불러올 수 없습니다. 파일 경로를 확인하세요: {FNG_FILE}")