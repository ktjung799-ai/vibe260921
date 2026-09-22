# -*- coding: utf-8 -*-
"""
대한민국 출생아수 / 합계출산율 / 자연증가 등 데이터 분석 - PyQt6 GUI 버전
원본: 출생아수__합계출산율__자연증가_등.xlsx (KOSIS, 1970~2025)

birth_analysis.py(콘솔/스크립트 버전)의 데이터 클렌징·분석 로직을 그대로 유지하되,
결과를 PyQt6 창에서 인터랙티브하게 확인할 수 있도록 GUI로 재구성했다.

탭 구성
  1) 그래프      : 콤보박스로 지표를 선택해 1970~2025 라인 그래프를 확인 (최고/최저 강조)
  2) 다각도 분석  : 콘솔 버전의 분석 리포트를 텍스트로 표시
  3) 연대별 통계  : 연대별 평균 출생아수/합계출산율 표
  4) 정제 데이터  : 클렌징이 끝난 전체 표(연도 x 지표)

메뉴에서 다른 형식이 같은 엑셀 파일을 열거나, 정제 데이터를 CSV로, 현재 그래프를 PNG로 저장할 수 있다.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------------
# 0. 한글 폰트 설정 (Windows: 맑은 고딕)
# ------------------------------------------------------------------
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

DEFAULT_SRC_FILE = "출생아수__합계출산율__자연증가_등.xlsx"

# 원본 지표명 -> 분석에서 사용할 짧은 컬럼명
COLUMN_MAP = {
    "출생아수(명)": "출생아수",
    "자연증가건수(명)": "자연증가건수",
    "조출생률(천명당)": "조출생률",
    "자연증가율(천명당)": "자연증가율",
    "합계출산율(명)": "합계출산율",
    "출생성비(명)": "출생성비",
}

# 그래프 콤보박스에 표시할 지표 -> 단위
INDICATOR_UNITS = {
    "출생아수": "명",
    "자연증가건수": "명",
    "조출생률": "천명당",
    "자연증가율": "천명당",
    "합계출산율": "명",
    "출생성비": "명",
}


# ------------------------------------------------------------------
# 1. 데이터 클렌징 (콘솔 버전과 동일한 로직)
# ------------------------------------------------------------------
def load_and_clean(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0, header=0)

    raw = raw.rename(columns={raw.columns[0]: "지표"})
    raw = raw.set_index("지표")
    raw = raw.rename(index=COLUMN_MAP)

    df = raw.T
    df.index.name = "연도"
    df.index = df.index.astype(int)

    df = df.replace("-", pd.NA)

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["출생아수", "자연증가건수"]:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


# ------------------------------------------------------------------
# 2. 다각도 분석 -> 콘솔 출력 대신 문자열/표로 반환
# ------------------------------------------------------------------
def build_decade_table(df: pd.DataFrame) -> pd.DataFrame:
    decade = (df.index // 10 * 10).astype(str) + "년대"
    return df.groupby(decade)[["출생아수", "합계출산율"]].mean().round(2)


def build_summary_text(df: pd.DataFrame) -> str:
    lines = []

    def sep(title):
        lines.append("=" * 60)
        lines.append(title)
        lines.append("=" * 60)

    sep("1) 기본 통계 (describe)")
    lines.append(df.describe().round(3).to_string())

    sep("\n2) 출생아수 최고/최저 연도")
    max_year = df["출생아수"].idxmax()
    min_year = df["출생아수"].dropna().idxmin()
    lines.append(f"최고: {max_year}년, {df.loc[max_year, '출생아수']:,}명")
    lines.append(f"최저: {min_year}년, {df.loc[min_year, '출생아수']:,}명")

    sep("\n3) 전년 대비 증감(YoY) — 출생아수 (최근 15개년)")
    df_yoy = df.copy()
    df_yoy["전년대비증감(명)"] = df_yoy["출생아수"].diff()
    df_yoy["전년대비증감률(%)"] = df_yoy["출생아수"].pct_change().mul(100).round(2)
    lines.append(df_yoy[["출생아수", "전년대비증감(명)", "전년대비증감률(%)"]].tail(15).to_string())

    sep("\n4) 1970년 대비 2024년(최신 확정치) 변화")
    if 1970 in df.index and 2024 in df.index:
        start_val = df.loc[1970, "출생아수"]
        end_val = df.loc[2024, "출생아수"]
        change_pct = (end_val - start_val) / start_val * 100
        lines.append(f"1970년: {start_val:,}명 -> 2024년: {end_val:,}명")
        lines.append(f"변화율: {change_pct:.1f}% (감소폭 {start_val - end_val:,}명)")

    sep("\n5) 최근 10년(2015~2024) 연평균 감소율(CAGR)")
    if 2015 in df.index and 2024 in df.index:
        v0, v1 = df.loc[2015, "출생아수"], df.loc[2024, "출생아수"]
        n = 2024 - 2015
        cagr = ((v1 / v0) ** (1 / n) - 1) * 100
        lines.append(f"2015년 {v0:,}명 -> 2024년 {v1:,}명, 연평균 {cagr:.2f}%")

    sep("\n6) 자연증가 데드크로스 시점 (자연증가건수 최초 음수 연도)")
    negative = df[df["자연증가건수"] < 0]
    if not negative.empty:
        lines.append(
            f"{negative.index[0]}년부터 인구 자연감소 시작 "
            f"(자연증가건수 {negative.iloc[0]['자연증가건수']:,}명)"
        )
    else:
        lines.append("자연증가건수가 음수로 전환된 연도 없음")

    sep("\n7) 출생아수와 합계출산율의 상관관계")
    corr = df[["출생아수", "합계출산율"]].corr().iloc[0, 1]
    lines.append(f"상관계수: {corr:.4f} (1에 가까울수록 강한 양의 상관관계)")

    sep("\n8) 초저출산(합계출산율 1.0 미만) 진입 연도")
    below_1 = df[df["합계출산율"] < 1.0]
    if not below_1.empty:
        lines.append(f"{below_1.index[0]}년 최초로 합계출산율 1.0 미만 진입")
        lines.append(below_1[["합계출산율", "출생아수"]].to_string())
    else:
        lines.append("합계출산율이 1.0 미만으로 내려간 연도 없음")

    return "\n".join(lines)


# ------------------------------------------------------------------
# 3. matplotlib 캔버스 (라인 그래프)
# ------------------------------------------------------------------
class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 6))
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)

    def plot_indicator(self, df: pd.DataFrame, indicator: str):
        self.ax.clear()
        series = df[indicator].dropna()

        self.ax.plot(
            series.index,
            series.values,
            color="#2563eb",
            linewidth=2,
            marker="o",
            markersize=3,
        )

        max_idx = series.idxmax()
        min_idx = series.idxmin()
        for yr, offset, va in [(max_idx, 18, "bottom"), (min_idx, -18, "top")]:
            val = series.loc[yr]
            unit = INDICATOR_UNITS.get(indicator, "")
            val_str = f"{val:,.0f}" if float(val).is_integer() else f"{val:,.2f}"
            self.ax.annotate(
                f"{yr}년\n{val_str}{unit}",
                xy=(yr, val),
                xytext=(0, offset),
                textcoords="offset points",
                ha="center",
                va=va,
                fontsize=9,
                color="#1e3a8a",
                fontweight="bold",
            )
            self.ax.scatter([yr], [val], color="#dc2626", zorder=5, s=40)

        unit = INDICATOR_UNITS.get(indicator, "")
        self.ax.set_title(
            f"대한민국 {indicator} 추이 ({df.index.min()}~{df.index.max()})",
            fontsize=14,
            fontweight="bold",
        )
        self.ax.set_xlabel("연도")
        self.ax.set_ylabel(f"{indicator}({unit})" if unit else indicator)
        self.ax.set_xlim(df.index.min(), df.index.max())
        y_min, y_max = series.min(), series.max()
        y_pad = (y_max - y_min) * 0.12 or 1
        self.ax.set_ylim(y_min - y_pad, y_max + y_pad)
        self.ax.set_xticks(range(df.index.min(), df.index.max() + 1, 5))
        self.ax.yaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")
        self.ax.grid(True, linestyle="--", alpha=0.4)
        self.fig.tight_layout()
        self.draw()


# ------------------------------------------------------------------
# 4. 메인 윈도우
# ------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("대한민국 출생아수 · 합계출산율 · 자연증가 분석 (1970~2025)")
        self.resize(1200, 800)

        self.df: pd.DataFrame | None = None
        self.current_path: str | None = None

        self._build_menu()
        self._build_ui()
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # 실행 폴더에 기본 파일이 있으면 자동 로드
        default_path = Path(DEFAULT_SRC_FILE)
        if default_path.exists():
            self.open_file(str(default_path))
        else:
            self.status.showMessage("파일 > 엑셀 파일 열기 로 데이터를 불러오세요.")

    # -- 메뉴바 --------------------------------------------------
    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("파일")

        open_action = QAction("엑셀 파일 열기...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.on_open_clicked)
        file_menu.addAction(open_action)

        save_csv_action = QAction("정제 데이터 CSV로 저장...", self)
        save_csv_action.triggered.connect(self.on_save_csv)
        file_menu.addAction(save_csv_action)

        save_png_action = QAction("현재 그래프 PNG로 저장...", self)
        save_png_action.triggered.connect(self.on_save_png)
        file_menu.addAction(save_png_action)

        file_menu.addSeparator()
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # -- 중앙 위젯(탭) ---------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 탭 1: 그래프
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)

        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("지표 선택:"))
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(list(INDICATOR_UNITS.keys()))
        self.indicator_combo.currentTextChanged.connect(self.on_indicator_changed)
        control_row.addWidget(self.indicator_combo)
        control_row.addStretch()
        chart_layout.addLayout(control_row)

        self.canvas = ChartCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.canvas)
        self.tabs.addTab(chart_tab, "그래프")

        # 탭 2: 다각도 분석 요약
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 10))
        self.tabs.addTab(self.summary_text, "다각도 분석")

        # 탭 3: 연대별 통계
        self.decade_table = QTableWidget()
        self.tabs.addTab(self.decade_table, "연대별 통계")

        # 탭 4: 정제 데이터
        self.data_table = QTableWidget()
        self.tabs.addTab(self.data_table, "정제 데이터")

    # -- 데이터 로드 & 갱신 ------------------------------------------
    def open_file(self, path: str):
        try:
            df = load_and_clean(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "파일 열기 오류", f"파일을 읽는 중 오류가 발생했습니다.\n\n{exc}")
            return

        self.df = df
        self.current_path = path
        self.refresh_all()
        self.status.showMessage(f"로드 완료: {path}  ({len(df)}개 연도)")

    def refresh_all(self):
        if self.df is None:
            return
        self.canvas.plot_indicator(self.df, self.indicator_combo.currentText())
        self.summary_text.setPlainText(build_summary_text(self.df))
        self._fill_table(self.decade_table, build_decade_table(self.df), index_name="연대")
        self._fill_table(self.data_table, self.df, index_name="연도")

    @staticmethod
    def _fill_table(table: QTableWidget, df: pd.DataFrame, index_name: str):
        table.clear()
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns) + 1)
        table.setHorizontalHeaderLabels([index_name] + list(df.columns))

        for row_pos, (idx, row) in enumerate(df.iterrows()):
            table.setItem(row_pos, 0, QTableWidgetItem(str(idx)))
            for col_pos, val in enumerate(row, start=1):
                if pd.isna(val):
                    text = ""
                elif isinstance(val, float):
                    text = f"{val:,.3f}".rstrip("0").rstrip(".")
                else:
                    text = f"{val:,}"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row_pos, col_pos, item)

        table.resizeColumnsToContents()

    # -- 이벤트 핸들러 ---------------------------------------------
    def on_indicator_changed(self, indicator: str):
        if self.df is not None:
            self.canvas.plot_indicator(self.df, indicator)

    def on_open_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "엑셀 파일 열기", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self.open_file(path)

    def on_save_csv(self):
        if self.df is None:
            QMessageBox.warning(self, "저장 불가", "먼저 데이터를 불러오세요.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "정제 데이터 CSV로 저장", "birth_cleaned.csv", "CSV Files (*.csv)"
        )
        if path:
            self.df.to_csv(path, encoding="utf-8-sig")
            self.status.showMessage(f"CSV 저장 완료: {path}")

    def on_save_png(self):
        if self.df is None:
            QMessageBox.warning(self, "저장 불가", "먼저 데이터를 불러오세요.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "그래프 PNG로 저장", "birth_chart.png", "PNG Files (*.png)"
        )
        if path:
            self.canvas.fig.savefig(path, dpi=150)
            self.status.showMessage(f"그래프 저장 완료: {path}")


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
