import os
import pandas as pd
import streamlit as st
import FinanceDataReader as fdr
from streamlit_lightweight_charts import renderLightweightCharts

# =========================
# 기본 설정
# =========================
st.set_page_config(layout="wide")

# =========================
# Sidebar: 기간 & 경로
# =========================
st.sidebar.header("설정")

start = st.sidebar.date_input(
    "시작일",
    value=pd.to_datetime("2025-01-14").date()
)
end = st.sidebar.date_input(
    "종료일",
    value=pd.to_datetime("2026-01-14").date()
)

oi_dir = st.sidebar.text_input(
    "OI CSV 폴더 경로",
    value=r"/Users/User1/sesac-mini-project/sesac-miniProject/zzimni/data/daily_outputs/"
)

# =========================
# 종목 설정
# =========================
STOCKS = {
    "삼성전자": {
        "ticker": "005930",
        "csv": "삼성전자_일별집계_OI_2025-01-14_2026-01-14.csv",
    },
    "하이닉스": {
        "ticker": "000660",
        "csv": "하이닉스_일별집계_OI_2025-01-14_2026-01-14.csv",
    },
    "현대차": {
        "ticker": "005380",
        "csv": "현대차_일별집계_OI_2025-01-14_2026-01-14.csv",
    },
}

# =========================
# 커뮤니티 지표 매핑
# =========================
OI_COLUMNS = {
    "과열지수(OI)": "과열지수_OI",
    "조회수": "조회수",
    "게시글수": "게시글수",
    "댓글수": "댓글수",
    "좋아요수": "좋아요수",
}

COLOR_MAP = {
    # 기준 지표 (가장 안정적인 중립색)
    "과열지수(OI)": "rgba(55, 55, 55, 0.6)",      # 다크 그레이
    # 커뮤니티 원천 지표 (주가/거래량과 충돌 없음)
    "조회수":       "rgba(140, 86, 75, 0.5)",     # 브라운
    "게시글수":     "rgba(148, 103, 189, 0.5)",   # 퍼플
    "댓글수":       "rgba(44, 160, 140, 0.5)",    # 틸(청록)
    "좋아요수":     "rgba(188, 189, 34, 0.5)",    # 올리브
}

# =========================
# Sidebar: 종목 / 지표 선택
# =========================
stock_name = st.sidebar.selectbox(
    "종목 선택",
    list(STOCKS.keys())
)

selected_metrics = st.sidebar.multiselect(
    "표시할 커뮤니티 지표",
    options=list(OI_COLUMNS.keys()),
    default=["과열지수(OI)"]
)

# =========================
# 데이터 로드 함수
# =========================
@st.cache_data
def load_price_data(ticker, start_date, end_date):
    df = fdr.DataReader(ticker, str(start_date), str(end_date)).reset_index()
    return df

@st.cache_data
def load_oi_csv(csv_path, start_date, end_date):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    df = df[
        (df["날짜"].dt.date >= start_date) &
        (df["날짜"].dt.date <= end_date)
    ].sort_values("날짜")
    return df

# =========================
# 시리즈 생성
# =========================
def make_candles(df):
    return [
        {
            "time": d.strftime("%Y-%m-%d"),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
        }
        for d, o, h, l, c in zip(
            df["Date"], df["Open"], df["High"], df["Low"], df["Close"]
        )
    ]

def make_volume_bars(df):
    return [
        {
            "time": d.strftime("%Y-%m-%d"),
            "value": float(v),
        }
        for d, v in zip(df["Date"], df["Volume"])
    ]

def build_oi_series(df, selected_metrics):
    series = []
    for name in selected_metrics:
        col = OI_COLUMNS[name]

        line = [
            {"time": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d, v in zip(df["날짜"], df[col])
        ]

        series.append({
            "type": "Line",
            "data": line,
            "options": {
                "color": COLOR_MAP.get(name, "#333333"),
                "lineWidth": 2,
                "priceScaleId": "left",
            },
        })
    return series

# =========================
# 차트 렌더링 함수
# =========================
def render_chart(title, height, price_series, oi_series, key, right_label, left_label):
    chart_options = {
        "height": height,
        "rightPriceScale": {
            "borderVisible": True,
            "autoScale": True,
        },
        "leftPriceScale": {
            "visible": True,
            "borderVisible": True,
            "autoScale": True,
        },
        "layout": {
            "background": {"type": "solid", "color": "white"},
            "textColor": "black",
        },
        "grid": {
            "vertLines": {"color": "rgba(197,203,206,0.3)"},
            "horzLines": {"color": "rgba(197,203,206,0.3)"},
        },
    }

    series = price_series + oi_series

    st.subheader(title)
    renderLightweightCharts(
        [{"chart": chart_options, "series": series}],
        key=key
    )
    st.caption(f"오른쪽 축: {right_label} / 왼쪽 축: {left_label}")

# =========================
# 실행
# =========================
stock = STOCKS[stock_name]
csv_path = os.path.join(oi_dir, stock["csv"])

if not os.path.exists(csv_path):
    st.error(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
    st.stop()

price_df = load_price_data(stock["ticker"], start, end)
oi_df = load_oi_csv(csv_path, start, end)

oi_series = build_oi_series(oi_df, selected_metrics)

# ---------- 위: 캔들 + 커뮤니티 지표 ----------
candles = make_candles(price_df)

price_series_top = [{
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

render_chart(
    title=f"{stock_name} 캔들 + 커뮤니티 지표",
    height=520,
    price_series=price_series_top,
    oi_series=oi_series,
    key="price_chart",
    right_label="주가(원)",
    left_label="커뮤니티 지표"
)

st.divider()

# ---------- 아래: 거래량 + 커뮤니티 지표 ----------
volume_bars = make_volume_bars(price_df)

price_series_bottom = [{
    "type": "Histogram",
    "data": volume_bars,
    "options": {
        "color": "rgba(100, 149, 237, 0.6)",
        "priceScaleId": "right",
    },
}]

render_chart(
    title=f"{stock_name} 거래량 + 커뮤니티 지표",
    height=320,
    price_series=price_series_bottom,
    oi_series=oi_series,
    key="volume_chart",
    right_label="거래량",
    left_label="커뮤니티 지표"
)

# =========================
# 데이터 미리보기
# =========================
with st.expander("CSV 데이터 미리보기"):
    st.dataframe(oi_df.head(20))
