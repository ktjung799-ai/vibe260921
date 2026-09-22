# -*- coding: utf-8 -*-
"""
대한민국 출생아수 / 합계출산율 / 자연증가 등 데이터 분석
원본: 출생아수__합계출산율__자연증가_등.xlsx (KOSIS, 1970~2025)

이 스크립트는 다음을 수행한다.
  1. 원본 엑셀(가로형 wide 포맷)을 읽어 데이터 클렌징 후 연도 index를 갖는
     깔끔한 표(long/tidy에 가까운 형태)로 변환
  2. 다각도 분석 (연대별 평균, 증감률, 최고/최저 연도, 상관관계 등)
  3. 1970~2025년 출생아수 추이를 라인 그래프로 시각화
"""

import matplotlib.pyplot as plt
import pandas as pd

# ------------------------------------------------------------------
# 0. 한글 폰트 설정 (Windows: 맑은 고딕)
# ------------------------------------------------------------------
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False  # 한글 폰트 사용 시 마이너스 기호 깨짐 방지

SRC_FILE = "출생아수__합계출산율__자연증가_등.xlsx"
CLEANED_CSV = "birth_cleaned.csv"
CHART_PNG = "birth_count_1970_2025.png"

# 원본 지표명 -> 분석에서 사용할 짧은 컬럼명
COLUMN_MAP = {
    "출생아수(명)": "출생아수",
    "자연증가건수(명)": "자연증가건수",
    "조출생률(천명당)": "조출생률",
    "자연증가율(천명당)": "자연증가율",
    "합계출산율(명)": "합계출산율",
    "출생성비(명)": "출생성비",
}


# ------------------------------------------------------------------
# 1. 데이터 클렌징
# ------------------------------------------------------------------
def load_and_clean(path: str = SRC_FILE) -> pd.DataFrame:
    # 시트명이 "데이터" / "메타정보" 이므로 첫 번째(데이터) 시트만 사용
    raw = pd.read_excel(path, sheet_name=0, header=0)

    # 1) 첫 컬럼("기본항목별")을 인덱스로 지정 → 행: 지표, 열: 연도(wide 포맷)
    raw = raw.rename(columns={raw.columns[0]: "지표"})
    raw = raw.set_index("지표")

    # 2) 지표명을 짧은 한글 컬럼명으로 정리 (분석용)
    raw = raw.rename(index=COLUMN_MAP)

    # 3) wide(지표 x 연도) → long이 다루기 쉬운 tidy 포맷(연도 x 지표)으로 전치
    df = raw.T
    df.index.name = "연도"

    # 4) 연도 인덱스를 정수로 변환
    df.index = df.index.astype(int)

    # 5) 결측치 처리: 2025년 합계출산율처럼 잠정 미집계 값은 '-' 문자열로 들어옴 → NaN
    df = df.replace("-", pd.NA)

    # 6) 모든 값 숫자형으로 변환 (문자열 섞여 있으면 강제로 NaN 처리)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 7) 정수형이 자연스러운 컬럼(인원수)은 nullable Int64로, 나머지는 float 유지
    for col in ["출생아수", "자연증가건수"]:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    # 8) 정렬 및 중복 제거(혹시 모를 경우 대비)
    df = df[~df.index.duplicated(keep="first")].sort_index()

    return df


# ------------------------------------------------------------------
# 2. 다각도 분석
# ------------------------------------------------------------------
def analyze(df: pd.DataFrame) -> None:
    print("=" * 60)
    print("1) 기본 정보")
    print("=" * 60)
    print(df.info())
    print()
    print(df.describe())

    print("\n" + "=" * 60)
    print("2) 연대(decade)별 평균 출생아수 / 합계출산율")
    print("=" * 60)
    decade = (df.index // 10 * 10).astype(str) + "년대"
    decade_stat = df.groupby(decade)[["출생아수", "합계출산율"]].mean().round(2)
    print(decade_stat)

    print("\n" + "=" * 60)
    print("3) 출생아수 최고/최저 연도")
    print("=" * 60)
    max_year = df["출생아수"].idxmax()
    min_year = df["출생아수"].dropna().idxmin()
    print(f"최고: {max_year}년, {df.loc[max_year, '출생아수']:,}명")
    print(f"최저: {min_year}년, {df.loc[min_year, '출생아수']:,}명")

    print("\n" + "=" * 60)
    print("4) 전년 대비 증감(YoY) — 출생아수")
    print("=" * 60)
    df_yoy = df.copy()
    df_yoy["전년대비증감(명)"] = df_yoy["출생아수"].diff()
    df_yoy["전년대비증감률(%)"] = df_yoy["출생아수"].pct_change().mul(100).round(2)
    print(df_yoy[["출생아수", "전년대비증감(명)", "전년대비증감률(%)"]].tail(15))

    print("\n" + "=" * 60)
    print("5) 1970년 대비 2024년(최신 확정치) 변화")
    print("=" * 60)
    start_year, end_year = 1970, 2024
    start_val = df.loc[start_year, "출생아수"]
    end_val = df.loc[end_year, "출생아수"]
    change_pct = (end_val - start_val) / start_val * 100
    print(f"{start_year}년: {start_val:,}명 -> {end_year}년: {end_val:,}명")
    print(f"변화율: {change_pct:.1f}% (감소폭 {start_val - end_val:,}명)")

    print("\n" + "=" * 60)
    print("6) 최근 10년(2015~2024) 연평균 감소율(CAGR)")
    print("=" * 60)
    v0, v1 = df.loc[2015, "출생아수"], df.loc[2024, "출생아수"]
    n = 2024 - 2015
    cagr = ((v1 / v0) ** (1 / n) - 1) * 100
    print(f"2015년 {v0:,}명 -> 2024년 {v1:,}명, 연평균 {cagr:.2f}%")

    print("\n" + "=" * 60)
    print("7) 자연증가 데드크로스 시점 (자연증가건수가 처음 음수가 된 연도)")
    print("=" * 60)
    negative = df[df["자연증가건수"] < 0]
    if not negative.empty:
        print(f"{negative.index[0]}년부터 인구 자연감소 시작 "
              f"(자연증가건수 {negative.iloc[0]['자연증가건수']:,}명)")

    print("\n" + "=" * 60)
    print("8) 출생아수와 합계출산율의 상관관계")
    print("=" * 60)
    corr = df[["출생아수", "합계출산율"]].corr().iloc[0, 1]
    print(f"상관계수: {corr:.4f} (1에 가까울수록 강한 양의 상관관계)")

    print("\n" + "=" * 60)
    print("9) 초저출산(합계출산율 1.0 미만) 진입 연도")
    print("=" * 60)
    below_1 = df[df["합계출산율"] < 1.0]
    if not below_1.empty:
        print(f"{below_1.index[0]}년 최초로 합계출산율 1.0 미만 진입")
        print(below_1[["합계출산율", "출생아수"]])


# ------------------------------------------------------------------
# 3. 라인 그래프: 1970~2025년 출생아수 추이
# ------------------------------------------------------------------
def plot_birth_trend(df: pd.DataFrame, out_path: str = CHART_PNG) -> None:
    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(
        df.index,
        df["출생아수"],
        color="#2563eb",
        linewidth=2,
        marker="o",
        markersize=3,
    )

    # 최고/최저 연도 강조
    max_year = df["출생아수"].idxmax()
    min_year = df["출생아수"].dropna().idxmin()
    for yr, label_offset, va in [(max_year, 18, "bottom"), (min_year, -18, "top")]:
        val = df.loc[yr, "출생아수"]
        ax.annotate(
            f"{yr}년\n{val:,}명",
            xy=(yr, val),
            xytext=(0, label_offset),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=9,
            color="#1e3a8a",
            fontweight="bold",
        )
        ax.scatter([yr], [val], color="#dc2626", zorder=5, s=40)

    ax.set_title("대한민국 출생아수 추이 (1970~2025)", fontsize=16, fontweight="bold")
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수(명)")
    ax.set_xlim(df.index.min(), df.index.max())
    y_min, y_max = df["출생아수"].min(), df["출생아수"].max()
    y_pad = (y_max - y_min) * 0.12
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_xticks(range(df.index.min(), df.index.max() + 1, 5))
    ax.yaxis.set_major_formatter(lambda x, _: f"{int(x):,}")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"\n그래프 저장 완료: {out_path}")
    plt.show()


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
if __name__ == "__main__":
    df = load_and_clean()

    df.to_csv(CLEANED_CSV, encoding="utf-8-sig")
    print(f"클렌징된 데이터 저장 완료: {CLEANED_CSV}\n")

    analyze(df)
    plot_birth_trend(df)
