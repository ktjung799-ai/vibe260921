"""코스피200 편입종목상위 크롤러 (PyQt6 GUI)

대상 페이지: https://finance.naver.com/sise/sise_index.naver?code=KPI200

이 페이지는 자바스크립트로 화면을 그리는 구조라, 받아온 HTML에는 종목 데이터가 없어
BeautifulSoup으로는 파싱할 수 없다. 화면이 데이터를 가져오는 네이버 증권 JSON API를
직접 호출한다. (예전 HTML 페이지 sise/entryJongmok.naver 는 서비스가 종료되었다.)

사용법:
    pip install requests openpyxl PyQt6
    python kospi200_top.py
조회한 종목은 표로 보여주며 CSV, 엑셀(xlsx)로 저장할 수 있다.
"""
import csv
import sys
import time

import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

API = "https://m.stock.naver.com/api/index/{code}/enrollStocks"
PAGE_SIZE = 50  # 서버가 한 번에 허용하는 최대치(100 이상은 오류)
DELAY = 0.5     # 요청 사이 대기(초)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}
FIELDS = ["순위", "종목코드", "종목명", "시장", "현재가", "전일비", "등락률(%)",
          "거래량", "거래대금(백만)", "시가총액(억)"]
DOWN = {"FALLING", "LOWER_LIMIT"}


# ---------------------------------------------------------------- 크롤링 로직
def to_num(text):
    """'272,500' -> 272500, 변환 불가('N/A' 등)이면 None"""
    try:
        return int(text.replace(",", ""))
    except (AttributeError, ValueError):
        try:
            return float(text.replace(",", ""))
        except (AttributeError, ValueError):
            return None


def parse_row(rank, item):
    down = item.get("compareToPreviousPrice", {}).get("name") in DOWN
    sign = -1 if down else 1
    diff = to_num(item.get("compareToPreviousClosePrice"))
    ratio = to_num(item.get("fluctuationsRatio"))
    if ratio is not None:
        ratio = round(abs(ratio) * sign, 2)  # 하락은 음수로 통일
    return {
        "순위": rank,
        "종목코드": item.get("itemCode", ""),
        "종목명": item.get("stockName", ""),
        "시장": item.get("stockExchangeType", {}).get("nameKor", ""),
        "현재가": to_num(item.get("closePrice")),
        "전일비": abs(diff) * sign if diff is not None else None,
        "등락률(%)": ratio,
        "거래량": to_num(item.get("accumulatedTradingVolume")),
        "거래대금(백만)": to_num(item.get("accumulatedTradingValue")),
        "시가총액(억)": to_num(item.get("marketValue")),
    }


def crawl(limit, code="KPI200", on_page=None, should_stop=None):
    """지수 편입종목을 시가총액 순서대로 limit개 가져온다.

    on_page(현재 개수) : 페이지를 받을 때마다 호출되는 진행 콜백
    should_stop()      : True를 반환하면 중단하고 그때까지의 결과를 돌려준다
    """
    session = requests.Session()
    rows, page = [], 1
    while len(rows) < limit:
        if should_stop and should_stop():
            break
        resp = session.get(
            API.format(code=code),
            params={"page": page, "pageSize": PAGE_SIZE},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            break
        for item in items:
            rows.append(parse_row(len(rows) + 1, item))
            if len(rows) >= limit:
                break
        if on_page:
            on_page(len(rows))
        if len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(DELAY)
    return rows


def save_csv(rows, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # 엑셀 한글 호환
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def save_xlsx(rows, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "KOSPI200"
    ws.append(FIELDS)
    for r in rows:
        ws.append([r[k] for k in FIELDS])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4F46E5")
        c.alignment = Alignment(horizontal="center")
    for col in "EFHIJ":
        for cell in ws[col][1:]:
            cell.number_format = "#,##0"
    for cell in ws["G"][1:]:
        cell.number_format = "0.00"
    for col, width in zip("ABCDEFGHIJ", (6, 10, 20, 8, 12, 10, 10, 14, 16, 16)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    wb.save(path)


# ---------------------------------------------------------------- GUI
NUMERIC = {"순위", "현재가", "전일비", "등락률(%)", "거래량", "거래대금(백만)", "시가총액(억)"}
COLORED = {"현재가", "전일비", "등락률(%)"}
UP_COLOR, DOWN_COLOR = QColor("#d32f2f"), QColor("#1976d2")  # 한국 증시 관례: 상승 빨강, 하락 파랑


class NumItem(QTableWidgetItem):
    """화면에는 천 단위 콤마로 보이지만 숫자 크기로 정렬되는 셀"""

    def __init__(self, value, digits=0):
        super().__init__("-" if value is None else f"{value:,.{digits}f}")
        self.value = value
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        if isinstance(other, NumItem):
            a = float("-inf") if self.value is None else self.value
            b = float("-inf") if other.value is None else other.value
            return a < b
        return super().__lt__(other)


class CrawlWorker(QThread):
    progress = pyqtSignal(int)
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, limit):
        super().__init__()
        self.limit = limit
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            rows = crawl(self.limit, on_page=self.progress.emit, should_stop=lambda: self._cancel)
        except requests.RequestException as e:
            self.failed.emit(f"데이터를 가져오지 못했습니다.\n{e}")
        except ValueError:
            self.failed.emit("응답을 해석하지 못했습니다.\n(API 주소가 바뀌었거나 접근이 제한되었을 수 있습니다)")
        else:
            self.done.emit(rows)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코스피200 편입종목상위")
        self.resize(1050, 700)
        self.rows = []
        self.worker = None

        self.spin = QSpinBox()
        self.spin.setRange(1, 200)
        self.spin.setValue(50)
        self.spin.setSuffix(" 개")
        self.fetch_btn = QPushButton("조회")
        self.fetch_btn.clicked.connect(self.fetch)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("종목명/코드 검색")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self.apply_filter)

        top = QHBoxLayout()
        top.addWidget(QLabel("상위"))
        top.addWidget(self.spin)
        top.addWidget(self.fetch_btn)
        top.addWidget(self.stop_btn)
        top.addStretch(1)
        top.addWidget(self.filter)

        self.table = QTableWidget(0, len(FIELDS))
        self.table.setHorizontalHeaderLabels(FIELDS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)  # 헤더 클릭으로 정렬
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(8)
        self.status = QLabel("조회 버튼을 눌러 주세요.")
        self.csv_btn = QPushButton("CSV 저장")
        self.xlsx_btn = QPushButton("엑셀 저장")
        self.csv_btn.clicked.connect(lambda: self.save("csv"))
        self.xlsx_btn.clicked.connect(lambda: self.save("xlsx"))
        self.update_save_buttons()

        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.csv_btn)
        bottom.addWidget(self.xlsx_btn)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.progress)
        layout.addLayout(bottom)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def update_save_buttons(self):
        has = bool(self.rows)
        self.csv_btn.setEnabled(has)
        self.xlsx_btn.setEnabled(has)

    def fetch(self):
        if self.worker and self.worker.isRunning():
            return
        limit = self.spin.value()
        self.progress.setRange(0, limit)
        self.progress.setValue(0)
        self.status.setText("조회 중...")
        self.fetch_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.spin.setEnabled(False)
        self.worker = CrawlWorker(limit)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.cancel()
            self.stop_btn.setEnabled(False)

    def on_done(self, rows):
        self.rows = rows
        self.fill_table(rows)
        self.update_save_buttons()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.status.setText(f"{len(rows)}개 종목 조회 완료 ({stamp})" if rows else "가져온 종목이 없습니다.")

    def on_failed(self, msg):
        self.status.setText("조회 실패")
        QMessageBox.warning(self, "조회 실패", msg)

    def on_finished(self):
        self.fetch_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.spin.setEnabled(True)

    def fill_table(self, rows):
        self.table.setSortingEnabled(False)  # 채우는 동안 정렬 끄기(행이 뒤섞이는 것 방지)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            color = None
            if r["등락률(%)"]:
                color = UP_COLOR if r["등락률(%)"] > 0 else DOWN_COLOR
            for j, key in enumerate(FIELDS):
                if key in NUMERIC:
                    item = NumItem(r[key], 2 if key == "등락률(%)" else 0)
                else:
                    item = QTableWidgetItem(str(r[key]))
                if color and key in COLORED:
                    item.setForeground(QBrush(color))
                self.table.setItem(i, j, item)
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.apply_filter()

    def apply_filter(self):
        q = self.filter.text().strip().lower()
        code_col, name_col = FIELDS.index("종목코드"), FIELDS.index("종목명")
        for i in range(self.table.rowCount()):
            text = (self.table.item(i, code_col).text() + " " + self.table.item(i, name_col).text()).lower()
            self.table.setRowHidden(i, bool(q) and q not in text)

    def save(self, kind):
        if not self.rows:
            return
        filt = "CSV (*.csv)" if kind == "csv" else "Excel (*.xlsx)"
        path, _ = QFileDialog.getSaveFileName(self, "저장", f"kospi200_top.{kind}", filt)
        if not path:
            return
        try:
            (save_csv if kind == "csv" else save_xlsx)(self.rows, path)
        except OSError as e:  # 파일이 엑셀에서 열려 있는 경우 등
            QMessageBox.critical(self, "저장 실패", str(e))
            return
        self.status.setText(f"저장 완료: {path}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
