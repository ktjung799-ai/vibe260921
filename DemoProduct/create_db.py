"""
sample.db 생성 스크립트
판매 데이터를 관리하기 위한 SQLite 데이터베이스를 만들고
Customers, Products, Orders, OrderDetails 테이블을 생성한다.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.db")


def create_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    # 외래키 제약조건 활성화
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Customers 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Customers (
            CustomerID  INTEGER PRIMARY KEY,
            FirstName   TEXT NOT NULL,
            LastName    TEXT NOT NULL,
            Email       TEXT
        );
    """)

    # Products 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Products (
            ProductID     INTEGER PRIMARY KEY,
            ProductName   TEXT NOT NULL,
            UnitPrice     REAL NOT NULL,
            UnitsInStock  INTEGER NOT NULL DEFAULT 0
        );
    """)

    # Orders 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Orders (
            OrderID      INTEGER PRIMARY KEY,
            CustomerID   INTEGER NOT NULL,
            OrderDate    DATE NOT NULL,
            TotalAmount  REAL NOT NULL,
            FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID)
        );
    """)

    # OrderDetails 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS OrderDetails (
            OrderDetailID  INTEGER PRIMARY KEY,
            OrderID        INTEGER NOT NULL,
            ProductID      INTEGER NOT NULL,
            Quantity       INTEGER NOT NULL,
            UnitPrice      REAL NOT NULL,
            FOREIGN KEY (OrderID) REFERENCES Orders (OrderID),
            FOREIGN KEY (ProductID) REFERENCES Products (ProductID)
        );
    """)

    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        create_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"sample.db 생성 완료: {DB_PATH}")
        print("생성된 테이블:", ", ".join(tables))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
