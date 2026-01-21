import os
import pandas as pd
import streamlit as st
import FinanceDataReader as fdr
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(page_title="삼성(블라인드) 일별집계 vs 주가/거래량", layout="wide")

# =========================
# 1) Sidebar (팀원 틀 느낌 유지)
# =========================
st.sidebar.header("설정")

DAILY_DIR = st.sidebar.text_input(
    "일별집계 폴더 경로",
    value=r"C:\Users\USER\sesac-miniProject\완료\daily_outputs"
)

# 폴더 안 CSV를 자동 탐색해서 선택
csv_candidates = []
if os.path.isdir(DAILY_DIR):
    csv_candidates = [f for f in os.listdir(DAILY_DIR) if f.lower().endswith(".csv")]

if csv_candidates:
    default_idx = 0
    if "삼성_일별집계.csv" in csv_candidates:
        default_idx = csv_candidates.index("삼성_일별집계.csv")

    DAILY_FILE = st.sidebar.selectbox("일별집계 CSV 선택", csv_candidates, index=default_idx)
    DAILY_PATH = os.path.join(DAILY_DIR, DAILY_FILE)
else:
    # 폴더 탐색이 안 되면 직접 전체 경로 입력
    DAILY_PATH = st.sidebar.text_input(
        "일별집계 CSV 전체 경로",
        value=os.path.join(DAILY_DIR, "삼성_일별집계.csv")
    )

TICKER = st.sidebar.text_input("주가 티커", value="005930").strip() or "005930"

# 비교할 지표(선택 1개) - 사용자가 원한 “하나씩 선택해서 겹쳐 비교”
METRIC_MAP = {
    "조회수": "조회수",
    "게시글수": "게시글수",
    "댓글수": "댓글수",
    "좋아요수": "좋아요수",
}
selected_metric_label = st.sidebar.selectbox("겹쳐 비교할 지표(1개 선택)", list(METRIC_MAP.keys()), index=0)
selected_metric_col = METRIC_MAP[selected_metric_label]

normalize_line = st.sidebar.checkbox("선택 지표를 0~100 정규화(패턴 비교용)", value=False)


# =========================
# 2) Data Load (일별집계 CSV)
# =========================
@st.cache_data(show_spinner=False)
def load_daily(path: str) -> pd.DataFrame:
    # 인코딩 이슈 대비
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp949")

    # 필수 컬럼 체크 (현재 파일 형태 기준)
    required = {"날짜", "게시글수", "조회수", "댓글수", "좋아요수"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"일별집계 CSV에 필수 컬럼이 없습니다: {sorted(missing)}")

    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"]).copy()
    df = df.sort_values("날짜").reset_index(drop=True)

    for c in ["게시글수", "조회수", "댓글수", "좋아요수"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["time"] = df["날짜"].dt.strftime("%Y-%m-%d")  # LWCharts time 포맷
    return df


def minmax_0_100(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series([50] * len(s), index=s.index)
    return (s - mn) / (mx - mn) * 100


daily = load_daily(DAILY_PATH)

# 기간 기본값을 “일별집계 데이터 범위”로
min_day = daily["날짜"].min().date()
max_day = daily["날짜"].max().date()

start, end = st.sidebar.date_input("기간", value=(min_day, max_day), min_value=min_day, max_value=max_day)
start_str = pd.Timestamp(start).strftime("%Y-%m-%d")
end_str = pd.Timestamp(end).strftime("%Y-%m-%d")

# 기간 필터
daily_f = daily[(daily["날짜"].dt.date >= start) & (daily["날짜"].dt.date <= end)].copy()
if daily_f.empty:
    st.warning("선택한 기간에 일별집계 데이터가 없습니다. 기간을 다시 선택하세요.")
    st.stop()


# =========================
# 3) 주가 데이터 (캔들/거래량) - 팀원 방식 유지
# =========================
@st.cache_data(show_spinner=False)
def load_price(ticker: str, start_s: str, end_s: str) -> pd.DataFrame:
    df = fdr.DataReader(ticker, start_s, end_s).reset_index()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df


price = load_price(TICKER, start_str, end_str)

candles = [
    {
        "time": d.strftime("%Y-%m-%d"),
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
    }
    for d, o, h, l, c in zip(price["Date"], price["Open"], price["High"], price["Low"], price["Close"])
]

vol = pd.to_numeric(price["Volume"], errors="coerce").fillna(0)
up = price["Close"] >= price["Open"]
volume_hist = [
    {
        "time": d.strftime("%Y-%m-%d"),
        "value": float(v),
        "color": "red" if bool(u) else "blue",
    }
    for d, v, u in zip(price["Date"], vol, up)
]


# =========================
# 4) Line Series (일별집계 지표)
# =========================
def make_line_series(df_daily: pd.DataFrame, col: str, color: str, scale_id: str = "left"):
    values = df_daily[col].copy()
    if normalize_line:
        values = minmax_0_100(values)

    line_data = [{"time": t, "value": float(v)} for t, v in zip(df_daily["time"], values)]
    return {
        "type": "Line",
        "data": line_data,
        "options": {
            "color": color,
            "lineWidth": 2,
            "priceScaleId": scale_id,  # 왼쪽 축
        },
    }


COLOR_MAP = {
    "조회수": "#FF9900",
    "게시글수": "#2E86DE",
    "댓글수": "#27AE60",
    "좋아요수": "#8E44AD",
}

# (A) 일별추이 4개 라인 (한 차트에 같이)
line_all = [
    make_line_series(daily_f, "게시글수", COLOR_MAP["게시글수"]),
    make_line_series(daily_f, "조회수", COLOR_MAP["조회수"]),
    make_line_series(daily_f, "댓글수", COLOR_MAP["댓글수"]),
    make_line_series(daily_f, "좋아요수", COLOR_MAP["좋아요수"]),
]

# (B/C) 선택 지표 1개 라인 (주가/거래량에 겹쳐 비교)
line_selected = make_line_series(daily_f, selected_metric_col, COLOR_MAP[selected_metric_label])


# =========================
# 5) Rendering (팀원 틀: chart_options + series + renderLightweightCharts)
# =========================
def render_lines_only(title: str, line_series_list, key: str):
    chart_options = {
        "height": 420,
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
        "layout": {"background": {"type": "solid", "color": "white"}, "textColor": "black"},
        "grid": {
            "vertLines": {"color": "rgba(197, 203, 206, 0.3)"},
            "horzLines": {"color": "rgba(197, 203, 206, 0.3)"},
        },
        "timeScale": {"timeVisible": True, "secondsVisible": False},
    }

    series = []
    for s in line_series_list:
        series.append(s)

    st.subheader(title)
    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)


def render_candle_with_line(title: str, candles_data, line_series, key: str):
    chart_options = {
        "height": 520,
        "rightPriceScale": {
            "scaleMargins": {"top": 0.1, "bottom": 0.0},
            "borderVisible": True,
            "autoScale": True,
        },
        "leftPriceScale": {
            "visible": True,
            "borderVisible": True,
            "autoScale": True,
            "scaleMargins": {"top": 0.1, "bottom": 0.1},
        },
        "layout": {"background": {"type": "solid", "color": "white"}, "textColor": "black"},
        "grid": {
            "vertLines": {"color": "rgba(197, 203, 206, 0.3)"},
            "horzLines": {"color": "rgba(197, 203, 206, 0.3)"},
        },
        "timeScale": {"timeVisible": True, "secondsVisible": False},
    }

    series = [
        {
            "type": "Candlestick",
            "data": candles_data,
            "options": {
                "upColor": "red",
                "downColor": "blue",
                "borderUpColor": "red",
                "borderDownColor": "blue",
                "wickUpColor": "red",
                "wickDownColor": "blue",
            },
        },
        line_series,
    ]

    st.subheader(title)
    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)


def render_volume_with_line(title: str, volume_data, line_series, key: str):
    chart_options = {
        "height": 420,
        "rightPriceScale": {
            "scaleMargins": {"top": 0.1, "bottom": 0.0},
            "borderVisible": True,
            "autoScale": True,
        },
        "leftPriceScale": {
            "visible": True,
            "borderVisible": True,
            "autoScale": True,
            "scaleMargins": {"top": 0.1, "bottom": 0.1},
        },
        "layout": {"background": {"type": "solid", "color": "white"}, "textColor": "black"},
        "grid": {
            "vertLines": {"color": "rgba(197, 203, 206, 0.3)"},
            "horzLines": {"color": "rgba(197, 203, 206, 0.3)"},
        },
        "timeScale": {"timeVisible": True, "secondsVisible": False},
    }

    series = [
        {
            "type": "Histogram",
            "data": volume_data,
            "options": {"priceFormat": {"type": "volume"}},
        },
        line_series,
    ]

    st.subheader(title)
    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)


# =========================
# 6) Page
# =========================
st.title("삼성(블라인드) 일별집계 기반 대시보드 (LWCharts 틀 유지)")

# KPI(기간 필터 기준)
c1, c2, c3, c4 = st.columns(4)
c1.metric("기간 내 게시글수 합", f"{int(daily_f['게시글수'].sum()):,}")
c2.metric("기간 내 조회수 합", f"{int(daily_f['조회수'].sum()):,}")
c3.metric("기간 내 좋아요수 합", f"{int(daily_f['좋아요수'].sum()):,}")
c4.metric("기간 내 댓글수 합", f"{int(daily_f['댓글수'].sum()):,}")

st.divider()

# (1) 일별추이 4개 지표 (한 번에)
render_lines_only(
    title="1) 일별추이(게시글수/조회수/댓글수/좋아요수)",
    line_series_list=line_all,
    key="daily_all_lines"
)

st.divider()

# (2) 선택 지표 vs 거래량(겹쳐 비교)
render_volume_with_line(
    title=f"2) {selected_metric_label} vs 거래량(Volume) (겹쳐 비교)",
    volume_data=volume_hist,
    line_series=line_selected,
    key="volume_overlay"
)

st.divider()

# (3) 선택 지표 vs 주가(캔들)(겹쳐 비교)
render_candle_with_line(
    title=f"3) {selected_metric_label} vs 주가(캔들) (겹쳐 비교)",
    candles_data=candles,
    line_series=line_selected,
    key="price_overlay"
)

st.caption(
    "축 안내: 오른쪽 축은 주가/거래량, 왼쪽 축은 블라인드 일별지표입니다. "
    + ("(선택 지표는 0~100 정규화)" if normalize_line else ""))
