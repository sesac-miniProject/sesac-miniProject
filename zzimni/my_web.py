
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

# =============================
# 0. 종목 설정
# =============================
STOCK_CONFIG = {
    "삼성전자": {
        "csv": "./data/daily_outputs/삼성전자_일별집계_OI_2025-01-14_2026-01-14.csv",
        "ticker": "005930.KS"
    },
    "하이닉스": {
        "csv": "./data/daily_outputs/하이닉스_일별집계_OI_2025-01-14_2026-01-14.csv",
        "ticker": "000660.KS"
    },
    "현대차": {
        "csv": "./data/daily_outputs/현대차_일별집계_OI_2025-01-14_2026-01-14.csv",
        "ticker": "005380.KS"
    }
}

# =============================
# 1. 데이터 로드
# =============================
@st.cache_data
def load_daily(csv_path):
    df = pd.read_csv(csv_path)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df

@st.cache_data
def load_stock_data(ticker, start, end):
    stock = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False
    )
    stock = stock.reset_index()
    stock = stock[["Date", "Close", "Volume"]]
    stock.columns = ["날짜", "종가", "거래량"]
    stock["날짜"] = pd.to_datetime(stock["날짜"])
    return stock

# =============================
# 2. UI
# =============================
st.title("📊 커뮤니티 지표 vs 주가 · 거래량")

stock_name = st.selectbox(
    "종목 선택",
    list(STOCK_CONFIG.keys())
)

metric_col = st.selectbox(
    "비교할 커뮤니티 지표",
    ["게시글수", "댓글수", "조회수", "좋아요수"]
)

# =============================
# 3. 데이터 불러오기
# =============================
config = STOCK_CONFIG[stock_name]

df = load_daily(config["csv"])

stock_df = load_stock_data(
    config["ticker"],
    df["날짜"].min(),
    df["날짜"].max()
)

# =============================
# 4. 요약 지표
# =============================
st.metric(
    f"{stock_name} 총 {metric_col}",
    int(df[metric_col].sum())
)

# =============================
# 5. 시각화 (2단 그래프)
# =============================
fig, (ax_top, ax_bottom) = plt.subplots(
    2, 1,
    figsize=(14, 9),
    sharex=True,
    gridspec_kw={"height_ratios": [2, 2]}
)

# ---------- (상단) 커뮤니티 지표 + 주가 ----------
ax_top.bar(
    df["날짜"],
    df[metric_col],
    alpha=0.6,
    label=metric_col
)
ax_top.set_ylabel(metric_col)

ax_top_price = ax_top.twinx()
ax_top_price.plot(
    stock_df["날짜"],
    stock_df["종가"],
    linewidth=2,
    color="black",
    label="주가"
)
ax_top_price.set_ylabel("주가 (원)")

ax_top.set_title(f"{stock_name} | {metric_col} vs 주가")

# ---------- (하단) 커뮤니티 지표 + 거래량 ----------
ax_bottom.bar(
    df["날짜"],
    df[metric_col],
    alpha=0.6,
    label=metric_col
)
ax_bottom.set_ylabel(metric_col)

ax_bottom_vol = ax_bottom.twinx()
ax_bottom_vol.plot(
    stock_df["날짜"],
    stock_df["거래량"],
    linewidth=1.8,
    # linestyle="--",
    color="tab:orange",
    label="거래량"
)
ax_bottom_vol.set_ylabel("거래량")

ax_bottom.set_title(f"{stock_name} | {metric_col} vs 거래량")

# ---------- 마무리 ----------
plt.xticks(rotation=45)
plt.tight_layout()

st.pyplot(fig)

# =============================
# 6. 데이터 미리보기
# =============================
with st.expander("데이터 미리보기"):
    st.dataframe(df.head(10))
