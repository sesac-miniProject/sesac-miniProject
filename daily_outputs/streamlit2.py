#########################################################



# 0. 필요한 라이브러리 설치 (한 번만)
#########################################################
# pip install FinanceDataReader statsmodels matplotlib pandas numpy

#########################################################
# 1. 데이터 로드
#########################################################

import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import statsmodels.api as sm
import matplotlib.pyplot as plt

# ---- 여기만 바꾸면 다른 종목도 자동 실행 ----
CSV_PATH = "삼성_일별집계.csv"   # <- 네 파일명
TICKER = "005930"                 # 삼성전자의 ticker

# 커뮤 데이터 로드
df = pd.read_csv(CSV_PATH, parse_dates=['날짜'])

# 컬럼 확인
print("[COMMUNITY DATA]")
print(df.head())

#########################################################
# 2. FinanceDataReader로 주가/거래량 다운로드
#########################################################

start = df['날짜'].min().strftime("%Y-%m-%d")
end = df['날짜'].max().strftime("%Y-%m-%d")

price = fdr.DataReader(TICKER, start, end).reset_index()
price = price.rename(columns={'Date':'날짜'})
price = price[['날짜','Close','Volume']]

print("[PRICE DATA]")
print(price.head())

#########################################################
# 3. Merge (날짜 기준)
#########################################################

data = pd.merge(df, price, on='날짜', how='inner').sort_values('날짜')

#########################################################
# 4. 수익률/변화율 계산
#########################################################

data['ret'] = data['Close'].pct_change()
data['vol_chg'] = data['Volume'].pct_change()

# T+1, T+3, T+4 시차
for k in [1,3,4]:
    data[f'ret_t+{k}'] = data['ret'].shift(-k)
    data[f'vol_t+{k}'] = data['vol_chg'].shift(-k)

#########################################################
# 5. Q1: 상관 분석 (단순)
#########################################################

cols = ['게시글수','댓글수','조회수','좋아요수',
        'ret_t+1','ret_t+3','ret_t+4',
        'vol_t+1','vol_t+3','vol_t+4']

print("\n=== [상관 분석] ===")
print(data[cols].corr()[['ret_t+1','ret_t+3','ret_t+4','vol_t+1','vol_t+3','vol_t+4']])

#########################################################
# 6. Q1: 단순 회귀 (OLS)
#########################################################

X = data[['게시글수','댓글수','조회수','좋아요수']]
X = sm.add_constant(X)

y = data['ret_t+1']

print("\n=== [OLS 회귀: ret_t+1] ===")
model = sm.OLS(y, X, missing='drop').fit()
print(model.summary())

#########################################################
# 7. Q2: 이벤트 스터디 (댓글 상위 10% 기준)
#########################################################

# 이벤트 기준 변수 (필요시 조회수/좋아요로 바꿔도 됨)
th = data['댓글수'].quantile(0.9)
event_days = data.loc[data['댓글수'] >= th, '날짜']

print(f"\n이벤트 발생일: {len(event_days)}일")

from collections import defaultdict
windows = defaultdict(list)

for day in event_days:
    for k in range(-3, 5): # -3,-2,-1,0,1,2,3,4
        d = day + pd.Timedelta(days=k)
        row = data.loc[data['날짜'] == d]
        if not row.empty:
            windows[k].append(float(row['ret']))

event_window = pd.DataFrame({
    'rel_day': sorted(windows.keys()),
    'avg_ret': [np.mean(windows[k]) for k in sorted(windows.keys())]
})

print("\n=== [이벤트 스터디 결과] ===")
print(event_window)

#########################################################
# 8. 시각화
#########################################################

plt.figure(figsize=(6,4))
plt.plot(event_window['rel_day'], event_window['avg_ret'], marker='o')
plt.axvline(0, linestyle='--', color='grey')
plt.grid(True)
plt.title("이벤트일 기준 ±3일 평균 수익률")
plt.xlabel("이벤트 기준 일수")
plt.ylabel("평균 수익률")
plt.show()

print("\n완료!")
