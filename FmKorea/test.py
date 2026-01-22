import os
import pandas as pd
import numpy as np
import streamlit as st
import FinanceDataReader as fdr
import plotly.express as px
from streamlit_lightweight_charts import renderLightweightCharts
from datetime import timedelta

# 페이지 설정
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
# 2. 데이터 로드 및 정제 함수
# =========================
@st.cache_data
def get_cleaned_analysis_data(fng_path, ticker, start_date, end_date):
    if not os.path.exists(fng_path): 
        return pd.DataFrame()

    # 수익률 계산을 위해 시작일보다 14일 앞선 데이터부터 로드
    fetch_start = start_date - timedelta(days=14)
    df_stock = fdr.DataReader(ticker, str(fetch_start), str(end_date))
    df_stock = df_stock.reset_index()
    df_stock['Date_Only'] = df_stock['Date'].dt.date

    df_fng = pd.read_csv(fng_path)
    df_fng["date"] = pd.to_datetime(df_fng["date"]).dt.date

    # [핵심] 영업일 기준 Inner Merge (주말/공휴일 자동 제거)
    merged = pd.merge(
        df_fng, 
        df_stock[['Date_Only', 'Open', 'High', 'Low', 'Close', 'Volume']], 
        left_on='date', 
        right_on='Date_Only', 
        how='inner'
    )

    # 변동률 계산: (오늘종가 - 어제종가) / 어제종가
    merged['Change_Pct'] = merged['Close'].pct_change() * 100

    # 차기 거래일 상승률: 영업일만 남은 상태에서 shift를 하여 주말을 건너뛴 다음 장날 데이터를 가져옴
    merged['Next_Trading_Day_Return'] = merged['Change_Pct'].shift(-1)

    # 사용자가 설정한 날짜 범위로 필터링
    merged = merged[(merged['date'] >= start_date) & (merged['date'] <= end_date)]

    # 인덱스 재설정 및 결측치 제거 (심리지수나 종가가 없는 경우)
    return merged.reset_index(drop=True)

# =========================
# 3. 사이드바 설정
# =========================
st.sidebar.header("📊 분석 설정")
start = st.sidebar.date_input("시작일", value=pd.to_datetime("2025-01-14").date())
end = st.sidebar.date_input("종료일", value=pd.to_datetime("2026-01-14").date())

target_stock = st.sidebar.selectbox("분석 종목 선택", ["삼성전자(005930)", "SK하이닉스(000660)"])

if "삼성" in target_stock:
    ticker, FNG_FILE = "005930", r"./data/samsung_fng.csv"
else:
    ticker, FNG_FILE = "000660", r"./data/hynix_fng.csv"

# =========================
# 4. 데이터 처리 및 메인 화면
# =========================
df_final = get_cleaned_analysis_data(FNG_FILE, ticker, start, end)

if not df_final.empty:
    st.title(f"🎯 {target_stock} 심리-데이터 상관관계 분석")
    st.info(f"💡 주말과 공휴일을 제외한 **{len(df_final)}거래일** 데이터를 분석합니다.")

    # --- [섹션 1] 날짜별 상세 분석 ---
    st.subheader("📅 특정 날짜 심리-주가 상세")
    available_dates = df_final['date'].tolist()
    selected_date = st.select_slider("날짜 선택 (거래일 기준)", options=available_dates, value=available_dates[-1])

    # 선택된 날짜의 데이터 인덱스 추출
    selected_row = df_final[df_final["date"] == selected_date]
    day_data = selected_row.iloc[0]
    curr_idx = selected_row.index[0]

    # 전일 대비 지수 변화량 계산
    f_delta = 0
    if curr_idx > 0:
        f_delta = round(day_data['fng_index'] - df_final.loc[curr_idx-1, 'fng_index'], 2)

    fval = day_data['fng_index']
    if fval >= 60: state, s_color = "탐욕 (Greed)", "#008000"
    elif fval <= 40: state, s_color = "공포 (Fear)", "#FF4B4B"
    else: state, s_color = "중립 (Neutral)", "gray"

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label=f"[{selected_date}] 지수", value=f"{fval} pts", delta=f"{f_delta}")
        st.markdown(f"<div class='status-box'>상태: <span style='color:{s_color}'>{state}</span></div>", unsafe_allow_html=True)
    with m2:
        st.metric("당일 종가", f"{int(day_data['Close']):,}원", f"{day_data['Change_Pct']:.2f}%")
    with m3:
        st.metric("당일 거래량", f"{int(day_data['Volume']):,}")
    with m4:
        # '다음 거래일' 데이터가 있는지 확인
        next_ret = day_data['Next_Trading_Day_Return']
        st.metric("차기 거래일 상승률", f"{next_ret:.2f}%" if not pd.isna(next_ret) else "데이터 없음")

    st.divider()

    # --- [섹션 2] 시계열 추세 분석 (Lightweight Charts) ---
    st.subheader("📈 시계열 추세")
    candles = [{"time": d.strftime("%Y-%m-%d"), "open": float(o), "high": float(h), "low": float(l), "close": float(c)} 
               for d, o, h, l, c in zip(df_final["date"], df_final["Open"], df_final["High"], df_final["Low"], df_final["Close"])]
    fng_line = [{"time": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df_final["date"], df_final["fng_index"])]

    renderLightweightCharts([{"chart": {"height": 350}, "series": [{"type": "Candlestick", "data": candles, "options": {"upColor": "red", "downColor": "blue"}}]}], key=f"p_chart_{ticker}")
    renderLightweightCharts([{"chart": {"height": 200}, "series": [{"type": "Line", "data": fng_line, "options": {"color": "#AB47BC", "lineWidth": 3}}]}], key=f"f_chart_{ticker}")

    st.divider()

    # --- [섹션 3] 상관관계 산점도 분석 (1줄에 1개씩) ---
    
    # 1. 펨코(Femco) 데이터 분석
    st.header("🏢 Source: 펨코(FM Korea)")
    corr_df = df_final.dropna(subset=['Next_Trading_Day_Return', 'Volume'])

    st.subheader("📊 [펨코] 심리 지수 vs 차기 거래일 상승률")
    fig_ret = px.scatter(
        corr_df, x="fng_index", y="Next_Trading_Day_Return",
        size="emotion_density", color="Next_Trading_Day_Return",
        color_continuous_scale="RdYlGn",
        labels={"fng_index": "오늘의 펨코 지수", "Next_Trading_Day_Return": "차기 거래일 상승률 (%)"},
        hover_data=["date"], trendline="ols"
    )
    fig_ret.update_layout(height=600)
    st.plotly_chart(fig_ret, use_container_width=True)
    st.info(f"📈 **펨코 수익률 상관계수:** `{corr_df['fng_index'].corr(corr_df['Next_Trading_Day_Return']):.3f}`")

    st.subheader("📊 [펨코] 심리 지수 vs 당일 거래량")
    fig_vol = px.scatter(
        corr_df, x="fng_index", y="Volume",
        size="emotion_density", color="fng_index",
        color_continuous_scale="Viridis",
        labels={"fng_index": "당일 펨코 지수", "Volume": "당일 거래량"},
        hover_data=["date"], trendline="ols"
    )
    fig_vol.update_layout(height=600)
    st.plotly_chart(fig_vol, use_container_width=True)
    st.info(f"📈 **펨코 거래량 상관계수:** `{corr_df['fng_index'].corr(corr_df['Volume']):.3f}`")

    # 2. 디시인사이드(DC Inside) 데이터 분석 추가
    st.divider()
    st.header("🏢 Source: 디시인사이드(DC Inside)")
    
    # 종목별 DC 파일 경로 설정
    if "삼성" in target_stock:
        DC_FILE = r"..\data\samsung_fng_dc.csv"
    else:
        DC_FILE = r"..\data\hynix_fng_dc.csv"
        
    df_dc = get_cleaned_analysis_data(DC_FILE, ticker, start, end)
    
    if not df_dc.empty:
        corr_dc = df_dc.dropna(subset=['Next_Trading_Day_Return', 'Volume'])

        st.subheader("📊 [디시] 심리 지수 vs 차기 거래일 상승률")
        fig_dc_ret = px.scatter(
            corr_dc, x="fng_index", y="Next_Trading_Day_Return",
            size="emotion_density", color="Next_Trading_Day_Return",
            color_continuous_scale="RdYlGn",
            labels={"fng_index": "오늘의 디시 지수", "Next_Trading_Day_Return": "차기 거래일 상승률 (%)"},
            hover_data=["date"], trendline="ols"
        )
        fig_dc_ret.update_layout(height=600)
        st.plotly_chart(fig_dc_ret, use_container_width=True)
        st.info(f"📈 **디시 수익률 상관계수:** `{corr_dc['fng_index'].corr(corr_dc['Next_Trading_Day_Return']):.3f}`")

        st.subheader("📊 [디시] 심리 지수 vs 당일 거래량")
        fig_dc_vol = px.scatter(
            corr_dc, x="fng_index", y="Volume",
            size="emotion_density", color="fng_index",
            color_continuous_scale="Viridis",
            labels={"fng_index": "당일 디시 지수", "Volume": "당일 거래량"},
            hover_data=["date"], trendline="ols"
        )
        fig_dc_vol.update_layout(height=600)
        st.plotly_chart(fig_dc_vol, use_container_width=True)
        st.info(f"📈 **디시 거래량 상관계수:** `{corr_dc['fng_index'].corr(corr_dc['Volume']):.3f}`")
    else:
        st.warning("디시인사이드 데이터 파일을 찾을 수 없습니다.")

else:
    st.error("데이터를 불러오거나 병합하는 데 실패했습니다. 파일 경로와 주식 코드를 확인해주세요.")
