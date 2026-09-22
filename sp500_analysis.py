"""
S&P 500 과거 데이터 분석
- 원본 CSV 클렌징 (날짜/숫자 포맷 정리, 결측/이상치 처리)
- Pandas를 활용한 다각도 분석 (기술 통계, 연도별 수익률, 이동평균, 변동성, 최대 낙폭 등)
- 종가 기준 2000.01 ~ 2019.12 라인 그래프 생성
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ---------- 0. 설정 ----------
BASE_DIR = Path(__file__).resolve().parent
SRC_FILE = BASE_DIR / "S&P 500 과거 데이터.csv"
CLEAN_FILE = BASE_DIR / "sp500_cleaned.csv"
CHART_FILE = BASE_DIR / "sp500_close_2000_2019.png"

# 한글 폰트 설정 (Windows 기본 맑은 고딕) + 마이너스 기호 깨짐 방지
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# ---------- 1. 데이터 로드 & 클렌징 ----------
def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = ["date", "close", "open", "high", "low", "volume", "change_pct"]

    # 날짜: "2019- 11- 14" 처럼 하이픈 뒤에 공백이 섞여 있어 정리 후 datetime 변환
    df["date"] = pd.to_datetime(
        df["date"].str.replace(r"-\s+", "-", regex=True).str.strip(),
        format="%Y-%m-%d",
        errors="coerce",
    )

    # 가격 컬럼: 천단위 콤마 제거 후 float 변환
    for col in ["close", "open", "high", "low"]:
        df[col] = (
            df[col].astype(str).str.replace(",", "", regex=False).astype(float)
        )

    # 변동률: '%' 제거 후 float(%) 값으로 변환
    df["change_pct"] = (
        df["change_pct"].astype(str).str.replace("%", "", regex=False).astype(float)
    )

    # 거래량: 지수(index) 데이터라 이 파일에는 값이 전부 비어 있음 -> 컬럼 드롭
    # (만약 실제 값이 있다면 'K'/'M'/'B' 단위 변환 로직이 별도로 필요합니다)
    if df["volume"].isna().all():
        df = df.drop(columns=["volume"])
    else:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    before = len(df)
    df = df.drop_duplicates(subset="date")
    df = df.dropna(subset=["date", "close", "open", "high", "low"])
    removed = before - len(df)
    if removed:
        print(f"[클렌징] 결측치/중복 {removed}행 제거")

    # 이상치 점검: 종가 0 이하, 고가 < 저가 등 비정상 행 제거
    bad_mask = (df["close"] <= 0) | (df["high"] < df["low"])
    if bad_mask.any():
        print(f"[클렌징] 이상치 {bad_mask.sum()}행 제거")
        df = df[~bad_mask]

    df = df.sort_values("date").reset_index(drop=True).set_index("date")
    return df


df = load_and_clean(SRC_FILE)
df.to_csv(CLEAN_FILE, encoding="utf-8-sig")
print(f"클렌징 완료: {len(df)}행, 기간 {df.index.min().date()} ~ {df.index.max().date()}")
print(f"정제된 데이터 저장 -> {CLEAN_FILE.name}\n")


# ---------- 2. 다각도 분석 ----------

# 2-1. 기본 기술 통계 (종가 기준)
print("=== 기술 통계 (종가) ===")
print(df["close"].describe().round(2))
print()

# 2-2. 일간 수익률 & 변동성
df["daily_return"] = df["close"].pct_change() * 100
annualized_vol = df["daily_return"].std() * np.sqrt(252)
print("=== 일간 수익률 통계 (%) ===")
print(df["daily_return"].describe().round(3))
print(f"연환산 변동성: {annualized_vol:.2f}%\n")

# 2-3. 이동평균선 (추세 분석용, 그래프에도 함께 사용 가능)
df["MA50"] = df["close"].rolling(50).mean()
df["MA200"] = df["close"].rolling(200).mean()

# 2-4. 연도별 요약 (시작가/종료가/최고/최저/연간수익률/변동성)
yearly = df.groupby(df.index.year).agg(
    시작가=("close", "first"),
    종료가=("close", "last"),
    최고가=("close", "max"),
    최저가=("close", "min"),
    연간변동성=("daily_return", "std"),
)
yearly["연간수익률(%)"] = (yearly["종료가"] / yearly["시작가"] - 1) * 100
print("=== 연도별 요약 (마지막 연도는 데이터가 12월 전까지만 있을 수 있음) ===")
print(yearly.round(2))
print()

best_year = yearly["연간수익률(%)"].idxmax()
worst_year = yearly["연간수익률(%)"].idxmin()
print(f"최고 수익률 연도: {best_year}년 ({yearly.loc[best_year, '연간수익률(%)']:.2f}%)")
print(f"최저 수익률 연도: {worst_year}년 ({yearly.loc[worst_year, '연간수익률(%)']:.2f}%)\n")

# 2-5. 최대 낙폭 (Max Drawdown): 전고점 대비 최대 하락폭
running_max = df["close"].cummax()
drawdown = (df["close"] - running_max) / running_max * 100
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()
print(f"=== 최대 낙폭(MDD) === {max_dd:.2f}% ({max_dd_date.date()} 기준)\n")

# 2-6. 기간 내 최고가/최저가 발생일
print(f"기간 내 최고 종가: {df['close'].max():,.2f} ({df['close'].idxmax().date()})")
print(f"기간 내 최저 종가: {df['close'].min():,.2f} ({df['close'].idxmin().date()})\n")

# 2-7. 월별 평균 종가 (최근 12개월만 예시 출력)
monthly_avg = df["close"].resample("ME").mean()
print("=== 월별 평균 종가 (최근 12개월) ===")
print(monthly_avg.tail(12).round(2))
print()


# ---------- 3. 종가 라인 그래프 (2000.01 ~ 2019.12) ----------
plot_df = df.loc["2000-01-01":"2019-12-31"]

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(plot_df.index, plot_df["close"], color="#1f77b4", linewidth=1.2)
ax.set_title("S&P 500 종가 추이 (2000.01 ~ 2019.12)", fontsize=14, pad=12)
ax.set_xlabel("날짜")
ax.set_ylabel("종가")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(CHART_FILE, dpi=150)
print(f"차트 저장 -> {CHART_FILE.name}")

plt.show()
