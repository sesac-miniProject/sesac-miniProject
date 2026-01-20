import os
import pandas as pd
import streamlit as st
import FinanceDataReader as fdr
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(layout="wide")  # wide 레이아웃 [web:21]

# =========================
# Sidebar: 설정
# =========================
st.sidebar.header("설정")

start = st.sidebar.date_input("시작일", value=pd.to_datetime("2025-01-14").date())
end = st.sidebar.date_input("종료일", value=pd.to_datetime("2026-01-14").date())

# CSV 경로(원시값 4컬럼이 들어있는 파일)
SAMSUNG_CSV = st.sidebar.text_input(
    "삼성 데이터 CSV 경로",
    value=r"C:\Users\Jeon\sesac-miniProject\data\samsung_data.csv",
)
HYNIX_CSV = st.sidebar.text_input(
    "하이닉스 데이터 CSV 경로",
    value=r"C:\Users\Jeon\sesac-miniProject\data\hynix_data.csv",
)

# CSV 컬럼 매핑(표시명 -> 실제 컬럼명)
RAW_METRICS = {
    "조회수(view)": "조회수",
    "게시글(post)": "게시글수",
    "댓글(comment)": "댓글수",
    "좋아요(like)": "좋아요수",
}

# 라인 색상
METRIC_COLOR = {
    "조회수(view)": "#FF9900",
    "게시글(post)": "#2E86DE",
    "댓글(comment)": "#27AE60",
    "좋아요(like)": "#8E44AD",
}

st.sidebar.subheader("삼성 원시지표 표시")
samsung_selected = st.sidebar.multiselect(
    "삼성 차트에 표시할 지표(원시값)",
    options=list(RAW_METRICS.keys()),
    default=["조회수(view)"],
    key="samsung_raw_select",
)  # multiselect는 list를 반환 [web:10]

st.sidebar.subheader("하이닉스 원시지표 표시")
hynix_selected = st.sidebar.multiselect(
    "하이닉스 차트에 표시할 지표(원시값)",
    options=list(RAW_METRICS.keys()),
    default=["조회수(view)"],
    key="hynix_raw_select",
)  # [web:10]

# =========================
# 공통 함수: 캔들/라인 데이터 생성
# =========================
def make_candles(ticker: str, start_date, end_date):
    df = fdr.DataReader(ticker, str(start_date), str(end_date)).reset_index()
    # DataReader 결과는 Date 인덱스와 Open/High/Low/Close 컬럼을 포함 [web:16]
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


def make_metric_line(csv_path: str, value_col: str, start_date, end_date):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    df = df[(df["날짜"].dt.date >= start_date) & (df["날짜"].dt.date <= end_date)].sort_values("날짜")

    line = [{"time": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df["날짜"], df[value_col])]
    return line


def build_metric_series(csv_path, metric_map, selected_keys, start_date, end_date):
    out = []
    if not os.path.exists(csv_path):
        st.warning(f"파일 없음: {csv_path}")
        return out

    for label in selected_keys:
        col = metric_map[label]
        try:
            line = make_metric_line(csv_path, col, start_date, end_date)
        except Exception as e:
            st.warning(f"컬럼/데이터 읽기 실패: {label} ({col}) / {e}")
            continue

        out.append(
            {
                "type": "Line",
                "data": line,
                "options": {
                    "color": METRIC_COLOR.get(label, "#333333"),
                    "lineWidth": 2,
                    "priceScaleId": "left",  # 보조축(왼쪽)에 원시지표 [web:4]
                },
            }
        )
    return out


# =========================
# 차트 렌더: 캔들 + 여러 라인
# =========================
def render_price_with_metrics(title: str, candles, metric_series_list, key: str):
    chart_options = {
        "height": 520,
        "rightPriceScale": {
            "borderVisible": True,
            "autoScale": True,
            "scaleMargins": {"top": 0.10, "bottom": 0.05},
        },
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
        }
    ]

    # 선택된 지표 라인만 추가
    series.extend(metric_series_list)

    st.subheader(title)
    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)  # 사용 예시 [web:2]
    st.caption("오른쪽 축: 가격(원), 왼쪽 축: 원시지표(조회수/게시글/댓글/좋아요). 사이드바에서 지표 토글 가능.")


# =========================
# 1) 위: 삼성(005930) + 삼성 원시지표(토글)
# =========================
samsung_candles = make_candles("005930", start, end)
samsung_metric_series = build_metric_series(SAMSUNG_CSV, RAW_METRICS, samsung_selected, start, end)

render_price_with_metrics(
    title="삼성전자(005930) 캔들 + 원시지표 토글",
    candles=samsung_candles,
    metric_series_list=samsung_metric_series,
    key="chart_samsung",
)

st.divider()

# =========================
# 2) 아래: 하이닉스(000660) + 하이닉스 원시지표(토글)
# =========================
hynix_candles = make_candles("000660", start, end)
hynix_metric_series = build_metric_series(HYNIX_CSV, RAW_METRICS, hynix_selected, start, end)

render_price_with_metrics(
    title="SK하이닉스(000660) 캔들 + 원시지표 토글",
    candles=hynix_candles,
    metric_series_list=hynix_metric_series,
    key="chart_hynix",
)
