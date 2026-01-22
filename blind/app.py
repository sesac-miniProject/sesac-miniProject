import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta

st.set_page_config(page_title="커뮤니티-주가 통합 정밀 분석기", layout="wide")

# --- 1. 데이터 로드 및 전처리 ---
@st.cache_data
def load_data(file, ticker):
    b_df = pd.read_csv(file)
    b_df['날짜'] = pd.to_datetime(b_df['날짜'])
    
    # 주가 데이터 가져오기
    s_df = yf.download(ticker, start=b_df['날짜'].min() - timedelta(days=14), 
                       end=b_df['날짜'].max() + timedelta(days=14), progress=False)
    if isinstance(s_df.columns, pd.MultiIndex): s_df.columns = s_df.columns.get_level_values(0)
    s_df = s_df.reset_index().rename(columns={'Date': '날짜'})
    s_df['날짜'] = pd.to_datetime(s_df['날짜']).dt.tz_localize(None)
    
    df = pd.merge(b_df, s_df, on='날짜', how='inner')
    
    # [수정] 종합지수 제거 및 필수 지표 계산
    df['수익률(%)'] = df['Close'].pct_change() * 100
    df['변동성(%)'] = ((df['High'] - df['Low']) / df['Open']) * 100
    return df

# --- 2. 사이드바 및 파일 인식 ---
st.sidebar.header("🔍 분석 설정")
comm_name = st.sidebar.selectbox("커뮤니티", ["블라인드", "에펨코리아", "디시인사이드"])
uploaded_file = st.sidebar.file_uploader(f"{comm_name} 데이터 업로드", type=['csv'])

# 파일명 기반 자동 기업 인식 로직
detected_company = "삼성전자" # 기본값
if uploaded_file:
    fname = uploaded_file.name
    if "하이닉스" in fname or "SK" in fname:
        detected_company = "SK하이닉스"
    elif "현대" in fname:
        detected_company = "현대차"
    elif "삼성" in fname:
        detected_company = "삼성전자"

# 사이드바 선택 상자 (파일명으로 자동 매칭된 값이 기본 선택됨)
company = st.sidebar.selectbox("대상 기업", ["삼성전자", "SK하이닉스", "현대차"], 
                               index=["삼성전자", "SK하이닉스", "현대차"].index(detected_company))

ticker_map = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS"}

if uploaded_file:
    df = load_data(uploaded_file, ticker_map[company])
    df_sorted = df.sort_values('날짜')

    # --- 섹션 1: 전체 흐름 분석 ---
    st.header(f"1️⃣ {comm_name} 반응과 시장의 연결고리")
    # [수정] 종합지수 항목 제거
    selected_metric = st.selectbox("비교 지표 선택:", ["조회수", "댓글수", "좋아요수", "게시글수"])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        fig_trend.add_trace(go.Bar(x=df_sorted['날짜'].dt.strftime('%Y-%m-%d'), y=df_sorted[selected_metric], 
                                   name="반응도", marker_color='orange', opacity=0.4), secondary_y=False)
        fig_trend.add_trace(go.Scatter(x=df_sorted['날짜'].dt.strftime('%Y-%m-%d'), y=df_sorted['Close'], 
                                       name="주가", line=dict(color='blue')), secondary_y=True)
        fig_trend.update_xaxes(type='category', nticks=15)
        st.plotly_chart(fig_trend, use_container_width=True)

    with col2:
        corr_vol = df[selected_metric].corr(df['Volume'])
        corr_vola = df[selected_metric].corr(df['변동성(%)'])
        st.subheader("📝 통계 핵심 요약")
        st.info(f"🤝 **거래량 상관관계: {corr_vol:.2f}**\n\n" + ("여론이 뜨거울수록 매매가 활발해집니다." if corr_vol > 0.4 else "여론과 실제 매매량은 큰 관련이 없습니다."))
        st.warning(f"🌪️ **변동성 상관관계: {corr_vola:.2f}**\n\n" + ("관심이 쏠리면 주가가 요동칩니다." if corr_vola > 0.4 else "관심도에 비해 가격 움직임은 차분합니다."))

    # --- 섹션 2: 상위 5% 정밀 분석 ---
    st.divider()
    st.header("2️⃣ 관심 폭발(상위 5%) 날짜 전후 정밀 분석")
    
    threshold = df[selected_metric].quantile(0.95)
    top_dates_df = df[df[selected_metric] >= threshold].sort_values(by=selected_metric, ascending=False)
    date_options = top_dates_df['날짜'].dt.date.tolist()
    
    selected_date = st.selectbox(f"분석할 날짜 선택 (총 {len(date_options)}개):", date_options)
    sel_dt = pd.to_datetime(selected_date)
    target_idx = df_sorted[df_sorted['날짜'] == sel_dt].index[0]
    focus_df = df_sorted.iloc[max(0, target_idx-5):min(len(df_sorted), target_idx+6)].copy()

    col3, col4 = st.columns([2, 1])
    with col3:
        fig_ev = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ev.add_trace(go.Candlestick(x=focus_df['날짜'].dt.strftime('%m-%d'), open=focus_df['Open'], 
                                       high=focus_df['High'], low=focus_df['Low'], close=focus_df['Close']), secondary_y=True)
        fig_ev.add_trace(go.Bar(x=focus_df['날짜'].dt.strftime('%m-%d'), y=focus_df['Volume'], 
                                marker_color='lightgray', opacity=0.5), secondary_y=False)
        fig_ev.update_xaxes(type='category')
        fig_ev.add_vline(x=sel_dt.strftime('%m-%d'), line_dash="dash", line_color="red")
        fig_ev.update_layout(height=450, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_ev, use_container_width=True)

    with col4:
        st.subheader("👀 데이터 읽어주기")
        # 전후 수익률 계산
        pre_ret = focus_df[focus_df['날짜'] < sel_dt]['수익률(%)'].sum()
        post_ret = focus_df[focus_df['날짜'] > sel_dt]['수익률(%)'].sum()
        
        # 쉬운 설명 로직
        if pre_ret > 3 and post_ret < -1:
            st.warning("⚠️ **'이미 늦었을지도?' 패턴**\n\n사람들이 커뮤니티에서 북적거리기 전에 주가가 이미 많이 올랐어요. 소문이 다 퍼진 뒤에는 주가가 오히려 떨어졌으니 주의가 필요한 구간이었습니다.")
        elif pre_ret < -3 and post_ret > 1:
            st.success("✨ **'분위기 반전' 패턴**\n\n계속 떨어지던 주가가 사람들의 뜨거운 관심과 함께 다시 기운을 차리고 상승하기 시작했네요!")
        elif abs(post_ret) < 1.5:
            st.info("⚖️ **'찻잔 속의 태풍' 패턴**\n\n커뮤니티는 정말 뜨거웠지만, 실제 주가는 크게 오르지도 내리지도 않고 평소처럼 차분하게 흘러갔습니다.")
        else:
            st.write("주가가 커뮤니티의 뜨거운 반응과 함께 활발하게 움직였습니다.")
        st.write(f"👉 전후 수익률 변화: {pre_ret:+.2f}% → {post_ret:+.2f}%")

    # --- 섹션 3: 데이터 종합 결론 ---
    st.divider()
    st.header("3️⃣ 상위 5% 데이터 종합 성적표")
    
    price_patterns = []
    vol_patterns = []

    for d in date_options:
        d_idx = df_sorted[df_sorted['날짜'] == pd.to_datetime(d)].index[0]
        pre_sum = df_sorted.iloc[max(0, d_idx-5):d_idx]['수익률(%)'].sum()
        post_sum = df_sorted.iloc[d_idx+1:min(len(df_sorted), d_idx+6)]['수익률(%)'].sum()
        
        if pre_sum > 2 and post_sum < -1: price_patterns.append("소문 끝 매도 시작")
        elif pre_sum < -2 and post_sum > 1: price_patterns.append("분위기 반전")
        elif abs(post_sum) < 1.5: price_patterns.append("그냥 시끌벅적")
        else: price_patterns.append("동반 상승")
        
        avg_vol = df_sorted.iloc[max(0, d_idx-5):d_idx]['Volume'].mean()
        cur_vol = df_sorted.loc[d_idx, 'Volume']
        if cur_vol > avg_vol * 1.5: vol_patterns.append("적극적 매매")
        else: vol_patterns.append("차분한 매매")

    p_counts = pd.Series(price_patterns).value_counts()
    v_counts = pd.Series(vol_patterns).value_counts()
    
    col_p, col_v = st.columns(2)
    with col_p:
        st.plotly_chart(px.pie(values=p_counts.values, names=p_counts.index, title="주가 반응 유형 분포", hole=0.4), use_container_width=True)
    with col_v:
        st.plotly_chart(px.pie(values=v_counts.values, names=v_counts.index, title="거래량 반응 유형 분포", hole=0.4), use_container_width=True)
    
    # [수정] 기업명 변수 자동 적용
    st.markdown(f"### 🔍 데이터가 말해주는 {company}의 특징")
    main_p = p_counts.idxmax()
    main_v = v_counts.idxmax()
    
    conclusion_text = f"**{company}** 주식은 관심 폭발 시 주로 **[{main_p}]**과(와) **[{main_v}]** 현상을 보입니다."
    st.info(conclusion_text)

    # 상관관계 기반 상세 풀이 (company 변수 적용)
    if main_p == "소문 끝 매도 시작":
        st.write(f"* **왜 이런 결론이 나왔나요?** {company}은 화력이 세지기 전 이미 주가가 오르는 경향이 포착되었습니다. 게시판이 뜨거울 때 들어오는 '뒷북 매수'를 주의해야 하는 종목입니다.")
    elif main_p == "분위기 반전":
        st.write(f"* **왜 이런 결론이 나왔나요?** {company}은 바닥권에서 화제가 되면 저가 매수가 붙어 상승으로 돌아서는 긍정적 특징이 있습니다.")
    else:
        st.write(f"* **왜 이런 결론이 나왔나요?** {company}은 게시판 화력과 주가 상관관계({corr_vola:.2f})가 낮습니다. 여론보다는 기업 자체 실적에 더 민감합니다.")

    st.write(f"👉 **{company} 대응 전략:** 현재 여론 지표와 주가 간의 상관관계를 볼 때, 커뮤니티 정보만으로 매매하기보다 실제 거래량 변화를 동반하는지 꼭 확인하세요.")

    st.write("#### 📊 상위 5% 이슈 날짜 전체 데이터")
    st.table(top_dates_df[['날짜', selected_metric, 'Close', 'Volume', '변동성(%)', '수익률(%)']].style.format({
        'Close': '{:,.0f}', 'Volume': '{:,.0f}', '변동성(%)': '{:.2f}%', '수익률(%)': '{:+.2f}%'
    }))
else:
    st.info("파일을 업로드하시면 파일명에 맞춰 해당 기업을 자동으로 분석합니다.")