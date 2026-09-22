# -*- coding: utf-8 -*-
"""
DemoProduct - 판매 데이터 관리 GUI (PyQt6)

sample.db(SQLite)의 Customers / Products / Orders / OrderDetails 테이블을
조회(출력)하고 추가·수정·삭제(입력)할 수 있는 화면을 제공한다.

실행:
    python demo_product_gui.py
"""
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtSql import (
    QSqlDatabase,
    QSqlQuery,
    QSqlRelation,
    QSqlRelationalDelegate,
    QSqlRelationalTableModel,
    QSqlTableModel,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.db")
STYLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.qss")


# --------------------------------------------------------------------------
# 데이터베이스 연결 / 보조 뷰 생성
# --------------------------------------------------------------------------
def open_database() -> QSqlDatabase:
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(DB_PATH)
    if not db.open():
        raise RuntimeError(db.lastError().text())

    # 주문(Orders) 탭에서 고객을 "성명"으로 콤보박스 표시하기 위한 보조 뷰
    QSqlQuery(
        "CREATE VIEW IF NOT EXISTS CustomerNames AS "
        "SELECT CustomerID, LastName || FirstName AS FullName FROM Customers;"
    )
    return db


# --------------------------------------------------------------------------
# PK(기본키) 컬럼은 직접 수정하지 못하도록 막는 모델
# --------------------------------------------------------------------------
class ReadOnlyPkTableModel(QSqlTableModel):
    def flags(self, index):
        base = super().flags(index)
        if index.column() == 0:
            base &= ~Qt.ItemFlag.ItemIsEditable
        return base


class ReadOnlyPkRelationalModel(QSqlRelationalTableModel):
    def flags(self, index):
        base = super().flags(index)
        if index.column() == 0:
            base &= ~Qt.ItemFlag.ItemIsEditable
        return base


# --------------------------------------------------------------------------
# 테이블 1개를 담당하는 공용 CRUD 탭 위젯
# --------------------------------------------------------------------------
class TablePage(QWidget):
    def __init__(
        self,
        table_name: str,
        headers: dict,
        search_options: dict,
        relations: dict | None = None,
        parent=None,
    ):
        """
        table_name    : 대상 테이블 이름
        headers       : {컬럼명: 한글 헤더} 순서대로 표시할 컬럼
        search_options: {콤보에 표시할 라벨: 필터 SQL 템플릿("{term}" 치환)}
        relations     : {컬럼명: (참조테이블, 참조키컬럼, 표시컬럼)} - 콤보박스로 입력
        """
        super().__init__(parent)
        self.table_name = table_name
        self.headers = headers
        self.search_options = search_options

        # ---- 모델 구성 -----------------------------------------------
        if relations:
            self.model = ReadOnlyPkRelationalModel(self)
        else:
            self.model = ReadOnlyPkTableModel(self)

        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.model.setTable(table_name)

        if relations:
            for column, (rel_table, rel_key, rel_display) in relations.items():
                col_index = self.model.fieldIndex(column)
                self.model.setRelation(col_index, QSqlRelation(rel_table, rel_key, rel_display))

        # select() 이후에는 관계(FK) 컬럼의 fieldIndex()가 참조 테이블의 표시 컬럼
        # 이름 기준으로 바뀌어 원래 컬럼명으로 더 이상 찾을 수 없으므로, select() 전에
        # (인덱스, 한글 라벨) 목록을 미리 만들어 둔다.
        header_indexes = [
            (self.model.fieldIndex(col_name), label) for col_name, label in headers.items()
        ]

        self.model.select()

        for col_index, label in header_indexes:
            self.model.setHeaderData(col_index, Qt.Orientation.Horizontal, label)

        # ---- 화면 구성 -------------------------------------------------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 검색 영역 (카드 스타일)
        search_card = QFrame()
        search_card.setObjectName("searchCard")
        search_bar = QHBoxLayout(search_card)
        search_bar.setContentsMargins(14, 10, 14, 10)
        search_bar.setSpacing(8)

        search_label = QLabel("🔍 검색 대상")
        search_label.setObjectName("searchLabel")
        search_bar.addWidget(search_label)

        self.search_combo = QComboBox()
        self.search_combo.addItems(list(search_options.keys()))
        search_bar.addWidget(self.search_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("검색어 입력 후 Enter")
        self.search_edit.returnPressed.connect(self.apply_search)
        search_bar.addWidget(self.search_edit, 1)

        search_btn = QPushButton("검색")
        search_btn.setObjectName("searchBtn")
        search_btn.clicked.connect(self.apply_search)
        search_bar.addWidget(search_btn)

        clear_btn = QPushButton("전체보기")
        clear_btn.setObjectName("clearBtn")
        clear_btn.clicked.connect(self.clear_search)
        search_bar.addWidget(clear_btn)

        layout.addWidget(search_card)

        # 테이블 뷰
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.view.verticalHeader().setVisible(False)
        self.view.setAlternatingRowColors(True)
        self.view.setShowGrid(True)
        if relations:
            self.view.setItemDelegate(QSqlRelationalDelegate(self.view))
        layout.addWidget(self.view)

        # 버튼 영역 (입력/저장/삭제)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        add_btn = QPushButton("➕ 추가")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self.add_row)
        btn_bar.addWidget(add_btn)

        del_btn = QPushButton("🗑 선택 삭제")
        del_btn.setObjectName("deleteBtn")
        del_btn.clicked.connect(self.delete_selected)
        btn_bar.addWidget(del_btn)

        save_btn = QPushButton("💾 저장")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_changes)
        btn_bar.addWidget(save_btn)

        revert_btn = QPushButton("↩ 변경 취소")
        revert_btn.setObjectName("revertBtn")
        revert_btn.clicked.connect(self.revert_changes)
        btn_bar.addWidget(revert_btn)

        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.setObjectName("refreshBtn")
        refresh_btn.clicked.connect(self.refresh)
        btn_bar.addWidget(refresh_btn)

        btn_bar.addStretch(1)

        self.count_label = QLabel()
        self.count_label.setObjectName("countBadge")
        btn_bar.addWidget(self.count_label)

        layout.addLayout(btn_bar)

        self.update_count_label()

    # ---- 동작 ----------------------------------------------------------
    def apply_search(self):
        term = self.search_edit.text().strip().replace("'", "''")
        template = self.search_options[self.search_combo.currentText()]
        self.model.setFilter(template.format(term=term) if term else "")
        self.model.select()
        self.update_count_label()

    def clear_search(self):
        self.search_edit.clear()
        self.model.setFilter("")
        self.model.select()
        self.update_count_label()

    def add_row(self):
        row = self.model.rowCount()
        self.model.insertRow(row)
        index = self.model.index(row, 1 if self.model.columnCount() > 1 else 0)
        self.view.scrollToBottom()
        self.view.setCurrentIndex(index)
        self.view.edit(index)

    def delete_selected(self):
        rows = sorted(
            {idx.row() for idx in self.view.selectionModel().selectedRows()}, reverse=True
        )
        if not rows:
            QMessageBox.information(self, "안내", "삭제할 행을 선택하세요.")
            return
        answer = QMessageBox.question(
            self, "삭제 확인", f"선택한 {len(rows)}건을 삭제하시겠습니까?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for row in rows:
            self.model.removeRow(row)
        self.save_changes()

    def save_changes(self):
        if self.model.submitAll():
            self.model.select()
            self.update_count_label()
            QMessageBox.information(self, "저장 완료", "변경 사항이 저장되었습니다.")
        else:
            QMessageBox.critical(
                self, "저장 실패", f"저장 중 오류가 발생했습니다.\n{self.model.lastError().text()}"
            )

    def revert_changes(self):
        self.model.revertAll()
        self.update_count_label()

    def refresh(self):
        self.model.select()
        self.update_count_label()

    def update_count_label(self):
        count_query = QSqlQuery()
        where = self.model.filter()
        sql = f"SELECT COUNT(*) FROM {self.table_name}"
        if where:
            sql += f" WHERE {where}"
        count_query.exec(sql)
        total = 0
        if count_query.next():
            total = count_query.value(0)
        self.count_label.setText(f"총 {total:,}건")

    def showEvent(self, event):
        super().showEvent(event)
        # 창이 처음 표시될 때 원본 데이터가 있는 컬럼 위주로 폭을 보기 좋게 맞춘다.
        self.view.resizeColumnsToContents()
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


# --------------------------------------------------------------------------
# 메인 윈도우
# --------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DemoProduct - 판매 데이터 관리")
        self.resize(1200, 760)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # ---- 상단 배너 ----
        banner = QFrame()
        banner.setObjectName("headerBanner")
        banner.setFixedHeight(64)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(22, 8, 22, 8)
        banner_layout.setSpacing(0)

        title_label = QLabel("🛒 DemoProduct 판매 데이터 관리")
        title_label.setObjectName("headerTitle")
        banner_layout.addWidget(title_label)

        subtitle_label = QLabel("고객 · 상품 · 주문 · 주문상세 통합 관리 시스템")
        subtitle_label.setObjectName("headerSubtitle")
        banner_layout.addWidget(subtitle_label)

        central_layout.addWidget(banner)

        tabs = QTabWidget()
        central_layout.addWidget(tabs)

        self.setCentralWidget(central)

        customers_page = TablePage(
            table_name="Customers",
            headers={
                "CustomerID": "고객ID",
                "FirstName": "이름",
                "LastName": "성",
                "Email": "이메일",
            },
            search_options={
                "이름": "FirstName LIKE '%{term}%'",
                "성": "LastName LIKE '%{term}%'",
                "이메일": "Email LIKE '%{term}%'",
            },
        )

        products_page = TablePage(
            table_name="Products",
            headers={
                "ProductID": "상품ID",
                "ProductName": "상품명",
                "UnitPrice": "단가",
                "UnitsInStock": "재고수량",
            },
            search_options={
                "상품명": "ProductName LIKE '%{term}%'",
            },
        )

        orders_page = TablePage(
            table_name="Orders",
            headers={
                "OrderID": "주문ID",
                "CustomerID": "고객",
                "OrderDate": "주문일자",
                "TotalAmount": "주문금액",
            },
            search_options={
                "주문ID": "Orders.OrderID = {term}",
                "주문일자(예: 2024)": "Orders.OrderDate LIKE '{term}%'",
                "고객명": (
                    "Orders.CustomerID IN "
                    "(SELECT CustomerID FROM Customers "
                    "WHERE FirstName LIKE '%{term}%' OR LastName LIKE '%{term}%')"
                ),
            },
            relations={"CustomerID": ("CustomerNames", "CustomerID", "FullName")},
        )

        order_details_page = TablePage(
            table_name="OrderDetails",
            headers={
                "OrderDetailID": "명세ID",
                "OrderID": "주문ID",
                "ProductID": "상품",
                "Quantity": "수량",
                "UnitPrice": "단가",
            },
            search_options={
                "주문ID": "OrderDetails.OrderID = {term}",
                "상품명": (
                    "OrderDetails.ProductID IN "
                    "(SELECT ProductID FROM Products WHERE ProductName LIKE '%{term}%')"
                ),
            },
            relations={"ProductID": ("Products", "ProductID", "ProductName")},
        )

        tabs.addTab(customers_page, "👤 고객")
        tabs.addTab(products_page, "📦 상품")
        tabs.addTab(orders_page, "🧾 주문")
        tabs.addTab(order_details_page, "📋 주문상세")

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(f"연결된 데이터베이스: {DB_PATH}")


def load_stylesheet() -> str:
    try:
        with open(STYLE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        # 스타일시트 파일이 없어도 앱은 기본 모양으로 동작한다.
        return "QWidget { font-family: '맑은 고딕'; font-size: 10pt; }"


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())

    try:
        open_database()
    except RuntimeError as exc:
        QMessageBox.critical(None, "DB 연결 실패", str(exc))
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
