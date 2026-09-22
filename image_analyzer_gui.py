# -*- coding: utf-8 -*-
"""
이미지 분석 GUI - PyQt6 + OpenAI Vision API

사진 파일을 업로드하면 OpenAI의 멀티모달 모델(gpt-4o 계열)에 이미지를 전달해
"이 사진에 무엇이 있는지" 분석한 설명을 받아와 화면에 보여준다.

    pip install PyQt6 openai

    setx OPENAI_API_KEY "sk-..."      (Windows, 새 터미널부터 적용)
    또는 앱 상단 입력창에 직접 API 키를 입력해도 된다.

    python image_analyzer_gui.py
"""
import base64
import os
import sys
from pathlib import Path

from openai import OpenAI
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]
DEFAULT_PROMPT = "이 사진에 무엇이 있는지 한국어로 자세히 설명해줘. 주요 사물, 분위기, 특징을 항목별로 정리해줘."
IMAGE_FILTER = "이미지 파일 (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}


def encode_image_to_data_url(path: str) -> str:
    """이미지 파일을 base64로 인코딩해 OpenAI API가 요구하는 data URL 형식으로 변환한다."""
    ext = Path(path).suffix.lower()
    mime = MIME_BY_EXT.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# --------------------------------------------------------------- 백그라운드 워커
class AnalyzeWorker(QThread):
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, api_key: str, model: str, image_path: str, prompt: str):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.image_path = image_path
        self.prompt = prompt

    def run(self):
        try:
            client = OpenAI(api_key=self.api_key)
            data_url = encode_image_to_data_url(self.image_path)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=1000,
            )
            text = response.choices[0].message.content or "(빈 응답이 반환되었습니다.)"
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"분석 중 오류가 발생했습니다.\n{e}")
            return
        self.finished_ok.emit(text)


# --------------------------------------------------------------- 메인 윈도우
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("이미지 분석 - OpenAI Vision")
        self.resize(1100, 750)

        self.image_path: str | None = None
        self.worker: AnalyzeWorker | None = None

        self._build_ui()

    def _build_ui(self):
        # ---- 상단: API 키 / 모델 선택
        self.api_key_input = QLineEdit(os.environ.get("OPENAI_API_KEY", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("OpenAI API 키 (환경변수 OPENAI_API_KEY에서 자동 로드됨)")

        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)

        top1 = QHBoxLayout()
        top1.addWidget(QLabel("API 키"))
        top1.addWidget(self.api_key_input, 1)
        top1.addWidget(QLabel("모델"))
        top1.addWidget(self.model_combo)

        # ---- 프롬프트 입력
        self.prompt_input = QPlainTextEdit(DEFAULT_PROMPT)
        self.prompt_input.setMaximumHeight(60)

        # ---- 좌: 이미지 미리보기 / 우: 분석 결과
        self.image_label = QLabel("이미지를 업로드해 주세요")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px dashed #999; background: #fafafa;")
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText("분석 결과가 여기에 표시됩니다.")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.image_label)
        splitter.addWidget(self.result_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # ---- 하단: 버튼 + 진행바
        self.open_btn = QPushButton("이미지 열기")
        self.open_btn.clicked.connect(self.open_image)
        self.analyze_btn = QPushButton("분석 시작")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.analyze)
        self.save_btn = QPushButton("결과 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_result)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 대기 상태에서는 애니메이션 없이 숨김 처리
        self.progress.setVisible(False)

        bottom = QHBoxLayout()
        bottom.addWidget(self.open_btn)
        bottom.addWidget(self.analyze_btn)
        bottom.addWidget(self.save_btn)
        bottom.addWidget(self.progress, 1)

        layout = QVBoxLayout()
        layout.addLayout(top1)
        layout.addWidget(self.prompt_input)
        layout.addWidget(splitter, 1)
        layout.addLayout(bottom)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    # ------------------------------------------------------------ 동작
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "이미지 열기", "", IMAGE_FILTER)
        if not path:
            return
        self.image_path = path
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "열기 실패", "이미지 파일을 불러오지 못했습니다.")
            self.image_path = None
            return
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.analyze_btn.setEnabled(True)
        self.result_box.clear()
        self.save_btn.setEnabled(False)

    def resizeEvent(self, event):
        # 창 크기가 바뀌면 미리보기 이미지도 다시 스케일링한다.
        super().resizeEvent(event)
        if self.image_path and self.image_label.pixmap():
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(
                    pixmap.scaled(
                        self.image_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

    def set_running(self, running: bool):
        self.analyze_btn.setEnabled(not running)
        self.open_btn.setEnabled(not running)
        self.progress.setVisible(running)

    def analyze(self):
        if not self.image_path:
            return
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "API 키 필요", "OpenAI API 키를 입력해 주세요.")
            return
        if self.worker and self.worker.isRunning():
            return

        prompt = self.prompt_input.toPlainText().strip() or DEFAULT_PROMPT
        self.result_box.setPlainText("분석 중입니다...")
        self.save_btn.setEnabled(False)

        self.worker = AnalyzeWorker(api_key, self.model_combo.currentText(), self.image_path, prompt)
        self.worker.finished_ok.connect(self.on_finished_ok)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(lambda: self.set_running(False))
        self.set_running(True)
        self.worker.start()

    def on_finished_ok(self, text: str):
        self.result_box.setPlainText(text)
        self.save_btn.setEnabled(True)

    def on_failed(self, msg: str):
        self.result_box.setPlainText("")
        QMessageBox.warning(self, "분석 실패", msg)

    def save_result(self):
        text = self.result_box.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "결과 저장", "image_analysis.txt", "Text Files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        QMessageBox.information(self, "저장 완료", f"결과를 저장했습니다.\n{path}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.wait(3000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
