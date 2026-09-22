# -*- coding: utf-8 -*-
"""
마켓컬리 상품 후기 감성 분석 - PyQt6 GUI

지정한 마켓컬리 상품 페이지에서 후기(댓글)를 약 N개(기본 300개) 크롤링한 뒤,
간단한 한국어 키워드 기반 감성사전으로 긍정/부정/중립을 분류하고
pandas로 집계해 화면 왼쪽에는 후기 리스트를, 오른쪽에는 막대그래프를 보여준다.

컬리 상품 상세 페이지는 후기 영역이 자바스크립트로 렌더링되고, 두 번째 페이지
부터는 추가 네트워크 요청 없이 클라이언트 쪽에 미리 준비된 데이터를 "다음"
버튼 클릭으로 펼쳐 보여주는 구조라 requests만으로는 후기를 모을 수 없다.
그래서 Selenium으로 실제 브라우저를 띄워 "다음" 버튼을 반복 클릭하며 화면에
렌더링된 후기 카드를 그대로 읽어온다.

    pip install selenium pandas matplotlib PyQt6
    (Chrome 브라우저가 설치되어 있어야 하며, Selenium 4.6+ 는 드라이버를 자동으로 내려받는다)

    python kurly_review_sentiment_gui.py
"""
import re
import sys
import time

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import pandas as pd
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

DEFAULT_URL = "https://www.kurly.com/goods/1000969096?collectionCode=sale231107"
CLICK_DELAY = 1.2  # 페이지 클릭 사이 대기(초): 렌더링 시간 확보 + 서버 부담 완화
MAX_EMPTY_RETRY = 2  # "다음"을 눌러도 새 후기가 안 늘어나는 경우 재시도 후 중단

# --------------------------------------------------------------- 감성사전 (규칙 기반)
POSITIVE_WORDS = [
    "맛있", "맛나", "맛좋", "좋아요", "좋은", "좋다", "좋았", "훌륭", "최고", "대만족",
    "만족", "신선", "부드럽", "부드러워", "촉촉", "고소", "담백", "육즙", "든든", "푸짐",
    "강추", "추천", "재구매", "또구매", "또 구매", "재주문", "또주문", "잘먹었", "잘 먹었",
    "감사", "친절", "빠른배송", "빠르게", "신속", "깔끔", "가성비", "짱", "완벽", "이쁘",
    "예뻐요", "합리적", "든든해요", "굿", "성공", "합격",
]
NEGATIVE_WORDS = [
    "별로", "실망", "아쉬", "질기", "질겨", "비려", "비린내", "냄새나", "상했", "상한",
    "부족", "불만", "최악", "안좋", "안 좋", "짜증", "늦어", "늦게", "파손", "터짐",
    "터졌", "물러", "물렀", "딱딱", "퍽퍽", "싱거", "짜다", "느끼", "다시는", "환불",
    "불친절", "불량", "곰팡이", "녹아서", "눅눅", "비추", "실패", "핏물", "누린내",
    "질감이 별로", "포장 엉망", "상태가 안", "차갑지 않",
]


def classify_sentiment(text: str) -> tuple[str, int]:
    """텍스트에 포함된 긍/부정 키워드 개수를 비교해 감성을 분류한다."""
    pos = sum(text.count(w) for w in POSITIVE_WORDS)
    neg = sum(text.count(w) for w in NEGATIVE_WORDS)
    score = pos - neg
    if score > 0:
        return "긍정", score
    if score < 0:
        return "부정", score
    return "중립", score


# --------------------------------------------------------------- 크롤링 (Selenium)
def build_driver(headless: bool = True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,2400")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=opts)


def find_review_tab(driver):
    for el in driver.find_elements("css selector", "button, a"):
        try:
            if "후기" in el.text:
                return el
        except Exception:
            continue
    return None


def scrape_current_cards(driver):
    """현재 렌더링된 후기 카드를 읽어온다. 클래스명이 바뀌어도 어느 정도 견디도록
    구조적 fallback(첫 h3/첫 p/날짜 정규식)을 함께 사용한다."""
    return driver.execute_script(
        r"""
        const cards = document.querySelectorAll("div[id^='review-']");
        return Array.from(cards).map(c => {
            const id = c.id;
            const author = (c.querySelector("span.e3ar37f9") || {}).innerText || "";
            const badgeEl = c.querySelector(".css-1fx0516") || c.querySelector("[class*='e3ar37f8'] div");
            const badge = badgeEl ? badgeEl.innerText : "";
            const optionEl = c.querySelector("h3.e3ar37f2") || c.querySelector("article h3");
            const option = optionEl ? optionEl.innerText : "";
            const bodyEl = c.querySelector("p.e3ar37f1") || c.querySelector("article p");
            const body = bodyEl ? bodyEl.innerText : "";
            const dateEl = c.querySelector("span.e3ar37f14");
            let date = dateEl ? dateEl.innerText : "";
            if (!date) {
                const m = c.innerText.match(/\d{4}\.\d{2}\.\d{2}/);
                date = m ? m[0] : "";
            }
            return {id, author, badge, option, body, date};
        });
        """
    )


def find_next_button(driver):
    buttons = driver.execute_script(
        """
        return Array.from(document.querySelectorAll("button")).filter(b => {
            const s = getComputedStyle(b);
            return s.backgroundImage && s.backgroundImage.includes("paging-next");
        });
        """
    )
    if buttons:
        return buttons[0]
    # fallback: aria-label 기반
    for el in driver.find_elements("css selector", "button[aria-label*='다음']"):
        return el
    return None


def crawl_reviews(url, target_count, headless, log, should_stop):
    """마켓컬리 상품 후기를 target_count개 정도 모아 dict 리스트로 반환한다."""
    driver = build_driver(headless=headless)
    collected = {}
    try:
        log(f"페이지 접속 중: {url}")
        driver.get(url)
        time.sleep(2)

        tab = find_review_tab(driver)
        if tab is None:
            raise RuntimeError("후기 탭을 찾지 못했습니다. 상품 URL을 확인해 주세요.")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
        time.sleep(0.3)
        tab.click()
        time.sleep(1.5)
        log("후기 탭 진입 완료. 수집을 시작합니다.")

        empty_retry = 0
        page = 0
        while len(collected) < target_count and not should_stop():
            page += 1
            cards = scrape_current_cards(driver)
            new_count = 0
            for c in cards:
                if c["id"] and c["id"] not in collected and c["body"].strip():
                    collected[c["id"]] = c
                    new_count += 1
            log(f"[{page}페이지] 새 후기 {new_count}건 (누적 {len(collected)}건)")

            if len(collected) >= target_count:
                break

            btn = find_next_button(driver)
            if btn is None:
                log("다음 버튼을 찾지 못해 수집을 종료합니다.")
                break
            if not btn.is_enabled():
                log("마지막 페이지에 도달했습니다.")
                break

            if new_count == 0:
                empty_retry += 1
                if empty_retry > MAX_EMPTY_RETRY:
                    log("더 이상 새로운 후기가 로드되지 않아 수집을 종료합니다.")
                    break
            else:
                empty_retry = 0

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.2)
            try:
                btn.click()
            except WebDriverException:
                driver.execute_script("arguments[0].click();", btn)
            time.sleep(CLICK_DELAY)
    finally:
        driver.quit()

    return list(collected.values())[:target_count]


# --------------------------------------------------------------- 백그라운드 워커
class CrawlWorker(QThread):
    log = pyqtSignal(str)
    review = pyqtSignal(dict)
    progress = pyqtSignal(int, int)
    failed = pyqtSignal(str)

    def __init__(self, url, target_count, headless):
        super().__init__()
        self.url = url
        self.target_count = target_count
        self.headless = headless
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            reviews = crawl_reviews(
                self.url,
                self.target_count,
                self.headless,
                log=lambda msg: self.log.emit(msg),
                should_stop=lambda: self._stop,
            )
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"크롤링 중 오류가 발생했습니다.\n{e}")
            return

        if not reviews:
            self.failed.emit("후기를 하나도 가져오지 못했습니다. URL/네트워크를 확인해 주세요.")
            return

        total = len(reviews)
        for i, r in enumerate(reviews, 1):
            if self._stop:
                self.log.emit("사용자가 중지했습니다.")
                break
            text = f"{r['option']} {r['body']}"
            sentiment, score = classify_sentiment(text)
            r["sentiment"] = sentiment
            r["score"] = score
            r["body"] = re.sub(r"\s+", " ", r["body"]).strip()  # 데이터 클렌징(공백 정리)
            self.review.emit(r)
            self.progress.emit(i, total)
        self.log.emit(f"완료: 총 {total}건 수집 및 분석")


# --------------------------------------------------------------- 막대그래프 캔버스
SENTIMENT_ORDER = ["긍정", "중립", "부정"]
SENTIMENT_COLOR = {"긍정": "#2563eb", "중립": "#9ca3af", "부정": "#dc2626"}


class BarChartCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 6))
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.update_counts({"긍정": 0, "중립": 0, "부정": 0})

    def update_counts(self, counts: dict):
        self.ax.clear()
        values = [counts.get(k, 0) for k in SENTIMENT_ORDER]
        colors = [SENTIMENT_COLOR[k] for k in SENTIMENT_ORDER]
        bars = self.ax.bar(SENTIMENT_ORDER, values, color=colors, width=0.55)

        total = sum(values)
        for bar, v in zip(bars, values):
            pct = f" ({v / total:.0%})" if total else ""
            self.ax.annotate(
                f"{v}{pct}",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=10,
                fontweight="bold",
            )

        self.ax.set_title(f"후기 감성 분포 (총 {total}건)", fontsize=13, fontweight="bold")
        self.ax.set_ylabel("건수")
        y_max = max(values) if values else 0
        self.ax.set_ylim(0, y_max * 1.2 + 1)
        self.ax.grid(axis="y", linestyle="--", alpha=0.4)
        self.fig.tight_layout()
        self.draw()


# --------------------------------------------------------------- 메인 윈도우
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("마켓컬리 후기 감성 분석 (긍정/부정 막대그래프)")
        self.resize(1300, 800)

        self.reviews: list[dict] = []
        self.worker: CrawlWorker | None = None

        self._build_ui()

    def _build_ui(self):
        # ---- 상단 입력 영역
        self.url_input = QLineEdit(DEFAULT_URL)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(10, 2000)
        self.count_spin.setSingleStep(10)
        self.count_spin.setValue(300)
        self.count_spin.setSuffix("건")
        self.headless_check = QCheckBox("백그라운드 실행(브라우저 창 숨김)")
        self.headless_check.setChecked(True)
        self.start_btn = QPushButton("크롤링 시작")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)

        top1 = QHBoxLayout()
        top1.addWidget(QLabel("상품 URL"))
        top1.addWidget(self.url_input, 1)
        top2 = QHBoxLayout()
        top2.addWidget(QLabel("수집 개수"))
        top2.addWidget(self.count_spin)
        top2.addWidget(self.headless_check)
        top2.addStretch()
        top2.addWidget(self.start_btn)
        top2.addWidget(self.stop_btn)

        # ---- 좌: 후기(댓글) 리스트 / 우: 막대그래프
        self.review_list = QListWidget()
        self.review_list.setWordWrap(True)
        self.review_list.setAlternatingRowColors(False)

        self.chart = BarChartCanvas(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.review_list)
        splitter.addWidget(self.chart)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # ---- 하단: 로그 + 진행바 + 저장
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(90)

        self.progress = QProgressBar()
        self.save_btn = QPushButton("CSV로 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_csv)
        bottom = QHBoxLayout()
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.save_btn)

        layout = QVBoxLayout()
        layout.addLayout(top1)
        layout.addLayout(top2)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.log_box)
        layout.addLayout(bottom)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    # ------------------------------------------------------------ 동작
    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.url_input.setEnabled(not running)
        self.count_spin.setEnabled(not running)
        self.headless_check.setEnabled(not running)

    def log(self, msg: str):
        self.log_box.append(msg)

    def start(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 필요", "상품 URL을 입력해 주세요.")
            return
        if self.worker and self.worker.isRunning():
            return

        self.reviews.clear()
        self.review_list.clear()
        self.log_box.clear()
        self.progress.setValue(0)
        self.save_btn.setEnabled(False)
        self.chart.update_counts({"긍정": 0, "중립": 0, "부정": 0})

        self.worker = CrawlWorker(url, self.count_spin.value(), self.headless_check.isChecked())
        self.worker.log.connect(self.log)
        self.worker.review.connect(self.add_review)
        self.worker.progress.connect(self.on_progress)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.set_running(True)
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)

    def add_review(self, r: dict):
        self.reviews.append(r)

        icon = {"긍정": "🙂", "중립": "😐", "부정": "🙁"}[r["sentiment"]]
        badge = f"[{r['badge']}] " if r["badge"] else ""
        text = f"{icon} {badge}{r['author']} · {r['date']}\n{r['option']}\n{r['body']}"
        item = QListWidgetItem(text)
        bg = {
            "긍정": QColor(230, 244, 255),
            "중립": QColor(240, 240, 240),
            "부정": QColor(255, 232, 232),
        }[r["sentiment"]]
        item.setBackground(bg)
        self.review_list.addItem(item)

        # pandas로 감성별 건수 집계 후 막대그래프 갱신
        df = pd.DataFrame(self.reviews)
        counts = df["sentiment"].value_counts().to_dict()
        self.chart.update_counts(counts)

    def on_progress(self, cur, total):
        self.progress.setMaximum(total)
        self.progress.setValue(cur)

    def on_failed(self, msg):
        self.log(msg.replace("\n", " "))
        QMessageBox.warning(self, "크롤링 실패", msg)

    def on_finished(self):
        self.set_running(False)
        self.save_btn.setEnabled(bool(self.reviews))

    def save_csv(self):
        if not self.reviews:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", "kurly_reviews.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        df = pd.DataFrame(self.reviews).drop_duplicates(subset="id")
        df.to_csv(path, index=False, encoding="utf-8-sig")
        self.log(f"저장 완료: {path} ({len(df)}건)")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
