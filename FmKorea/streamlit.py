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

# --- (추가) 가중치=1 OI 파일 매핑: 파일명만 맞추면 됨 ---
SAMSUNG_OI_FILES = {
    "조회수(view)":   "samsung_view_1.csv",
    "게시글(post)":   "samsung_post_1.csv",
    "댓글(comment)":  "samsung_comment_1.csv",
    "좋아요(like)":   "samsung_like_1.csv",
}
HYNIX_OI_FILES = {
    "조회수(view)":   "hynix_view_1.csv",
    "게시글(post)":   "hynix_post_1.csv",
    "댓글(comment)":  "hynix_comment_1.csv",
    "좋아요(like)":   "hynix_like_1.csv",
}

OI_COLOR = {
    "조회수(view)":  "#FF9900",
    "게시글(post)":  "#2E86DE",
    "댓글(comment)": "#27AE60",
    "좋아요(like)":  "#8E44AD",
}

# --- (추가) 토글 UI: 종목별 멀티셀렉트 ---
st.sidebar.subheader("삼성 OI 표시(가중치=1)")
samsung_selected = st.sidebar.multiselect(
    "삼성 차트에 표시할 OI",
    options=list(SAMSUNG_OI_FILES.keys()),
    default=["조회수(view)"],
    key="samsung_oi_select"
)  # 멀티셀렉트는 선택 리스트를 반환 [web:464]

st.sidebar.subheader("하이닉스 OI 표시(가중치=1)")
hynix_selected = st.sidebar.multiselect(
    "하이닉스 차트에 표시할 OI",
    options=list(HYNIX_OI_FILES.keys()),
    default=["조회수(view)"],
    key="hynix_oi_select"
)  # [web:464]

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

# =========================
# (수정) 여러 OI 라인을 받도록 변경
# =========================
def render_price_with_oi(title: str, candles, oi_series_list, key: str):
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

    # ✅ 선택된 OI 라인들만 추가(활성), 미선택은 추가하지 않음(비활성)
    for s in oi_series_list:
        series.append(s)

    st.subheader(title)
    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)
    st.caption("오른쪽 축: 가격(원), 왼쪽 축: 과열지수(OI). 사이드바에서 OI 라인을 켜고 끌 수 있음.")

# =========================
# 종목별 OI 시리즈 생성
# =========================
def build_oi_series(oi_dir, file_map, selected_keys, start_date, end_date):
    out = []
    for name in selected_keys:
        csv_path = os.path.join(oi_dir, file_map[name])
        if not os.path.exists(csv_path):
            st.warning(f"파일 없음: {csv_path}")
            continue
        line = make_oi_line(csv_path, start_date, end_date)
        out.append({
            "type": "Line",
            "data": line,
            "options": {
                "color": OI_COLOR.get(name, "#333333"),
                "lineWidth": 2,
                "priceScaleId": "left",  # 왼쪽 축에 OI [web:265]
            },
        })
    return out

# =========================
# 1) 위: 삼성(005930) + 삼성 OI(토글)
# =========================
samsung_candles = make_candles("005930", start, end)
samsung_oi_series = build_oi_series(oi_dir, SAMSUNG_OI_FILES, samsung_selected, start, end)

render_price_with_oi(
    title="삼성전자(005930) 캔들 + OI(가중치=1) 토글",
    candles=samsung_candles,
    oi_series_list=samsung_oi_series,
    key="chart_samsung"
)

st.divider()

# =========================
# 2) 아래: 하이닉스(000660) + 하이닉스 OI(토글)
# =========================
hynix_candles = make_candles("000660", start, end)
hynix_oi_series = build_oi_series(oi_dir, HYNIX_OI_FILES, hynix_selected, start, end)

render_price_with_oi(
    title="SK하이닉스(000660) 캔들 + OI(가중치=1) 토글",
    candles=hynix_candles,
    oi_series_list=hynix_oi_series,
    key="chart_hynix"
)
