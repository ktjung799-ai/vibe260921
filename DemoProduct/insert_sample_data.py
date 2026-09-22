# -*- coding: utf-8 -*-
"""
매출 집계용 샘플 데이터 생성 스크립트

- Customers, Products : 한국어 이름/상품명으로 생성
- Orders              : 2023~2025년 사이 약 10,000건, TotalAmount는 5,000~100,000원 사이 무작위
- OrderDetails        : 주문당 1~3건, 각 라인은 실제 상품 단가를 사용
"""
import os
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.db")

random.seed(42)  # 재현 가능한 결과를 위한 고정 시드

# --------------------------------------------------------------------------
# 1) 고객 데이터 (한국어 성/이름 조합)
# --------------------------------------------------------------------------
SURNAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
]

GIVEN_NAMES = [
    "민준", "서연", "도윤", "서준", "하은", "지호", "지우", "지민", "수빈", "예은",
    "유준", "하윤", "시우", "채원", "은우", "다은", "승우", "소율", "준우", "지안",
    "우진", "서윤", "현우", "지유", "건우", "나윤", "선호", "예린", "동현", "수아",
    "재원", "은서", "태윤", "유나", "민재", "가은", "성민", "지아", "영훈", "혜원",
]

EMAIL_DOMAINS = ["naver.com", "gmail.com", "daum.net", "hanmail.net", "kakao.com"]


def random_email(first_name_en_idx: int, last_name_en_idx: int, cust_id: int) -> str:
    domain = random.choice(EMAIL_DOMAINS)
    return f"user{cust_id}@{domain}"


def build_customers(n: int):
    customers = []
    for cust_id in range(1, n + 1):
        last_name = random.choice(SURNAMES)          # 성 (LastName)
        first_name = random.choice(GIVEN_NAMES)       # 이름 (FirstName)
        email = f"user{cust_id}@{random.choice(EMAIL_DOMAINS)}"
        customers.append((cust_id, first_name, last_name, email))
    return customers


# --------------------------------------------------------------------------
# 2) 상품 데이터 (카테고리별 한국어 상품명)
# --------------------------------------------------------------------------
PRODUCTS_BY_CATEGORY = {
    "전자제품": [
        "무선이어폰", "블루투스스피커", "스마트워치", "노트북", "태블릿PC",
        "무선충전기", "게이밍마우스", "기계식키보드", "웹캠", "모니터",
    ],
    "식품": [
        "유기농쌀", "제주감귤세트", "강원도감자", "전라도김치", "흑임자죽",
        "견과류세트", "수제청", "유자차", "홍삼정", "곶감세트",
    ],
    "생활용품": [
        "극세사수건세트", "스테인리스텀블러", "usb가습기", "접이식우산", "실리콘주방용품세트",
        "다용도수납박스", "극세사이불", "메모리폼베개", "천연방향제", "청소용밀대",
    ],
    "의류": [
        "기본반팔티셔츠", "후드집업", "데님청바지", "니트가디건", "캠핑모자",
        "경량등산자켓", "쿠션운동화", "발목양말세트", "방한장갑", "울목도리",
    ],
    "도서문구": [
        "베스트셀러소설", "자기계발서", "만년필", "스프링노트", "색연필세트",
        "가죽다이어리", "점착식포스트잇", "클리어파일세트", "데스크캘린더", "마스킹테이프세트",
    ],
    "뷰티": [
        "수분크림", "자외선차단크림", "립밤세트", "헤어에센스", "약산성클렌징폼",
        "마스크팩세트", "핸드크림세트", "바디로션", "센슈얼향수", "미니헤어드라이어",
    ],
}


def build_products():
    products = []
    product_id = 1
    for category, names in PRODUCTS_BY_CATEGORY.items():
        for name in names:
            unit_price = random.choice(
                [1500, 3000, 5900, 8900, 12000, 15000, 19800, 25000,
                 32000, 45000, 59000, 79000, 99000, 128000, 159000]
            )
            units_in_stock = random.randint(0, 500)
            full_name = f"[{category}] {name}"
            products.append((product_id, full_name, unit_price, units_in_stock))
            product_id += 1
    return products


# --------------------------------------------------------------------------
# 3) 주문 데이터 (2023-01-01 ~ 2025-12-31, 약 10,000건)
# --------------------------------------------------------------------------
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days


def random_order_date() -> str:
    offset = random.randint(0, TOTAL_DAYS)
    return (START_DATE + timedelta(days=offset)).isoformat()


def build_orders(n: int, customer_ids: list):
    orders = []
    for order_id in range(1, n + 1):
        customer_id = random.choice(customer_ids)
        order_date = random_order_date()
        total_amount = round(random.uniform(5000, 100000), -2)  # 100원 단위로 반올림
        orders.append((order_id, customer_id, order_date, total_amount))
    return orders


# --------------------------------------------------------------------------
# 4) 주문 명세 데이터 (주문당 1~3건)
# --------------------------------------------------------------------------
def build_order_details(order_ids: list, products: list):
    details = []
    detail_id = 1
    product_price_map = {p[0]: p[2] for p in products}
    product_ids = list(product_price_map.keys())

    for order_id in order_ids:
        line_count = random.randint(1, 3)
        chosen_products = random.sample(product_ids, k=min(line_count, len(product_ids)))
        for product_id in chosen_products:
            quantity = random.randint(1, 5)
            unit_price = product_price_map[product_id]
            details.append((detail_id, order_id, product_id, quantity, unit_price))
            detail_id += 1
    return details


def main():
    n_customers = 500
    n_orders = 10000

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        # 기존 데이터 초기화 (재실행 대비)
        cur.execute("DELETE FROM OrderDetails;")
        cur.execute("DELETE FROM Orders;")
        cur.execute("DELETE FROM Products;")
        cur.execute("DELETE FROM Customers;")

        customers = build_customers(n_customers)
        products = build_products()

        cur.executemany(
            "INSERT INTO Customers (CustomerID, FirstName, LastName, Email) VALUES (?, ?, ?, ?);",
            customers,
        )
        cur.executemany(
            "INSERT INTO Products (ProductID, ProductName, UnitPrice, UnitsInStock) VALUES (?, ?, ?, ?);",
            products,
        )

        customer_ids = [c[0] for c in customers]
        orders = build_orders(n_orders, customer_ids)
        cur.executemany(
            "INSERT INTO Orders (OrderID, CustomerID, OrderDate, TotalAmount) VALUES (?, ?, ?, ?);",
            orders,
        )

        order_ids = [o[0] for o in orders]
        order_details = build_order_details(order_ids, products)
        cur.executemany(
            "INSERT INTO OrderDetails (OrderDetailID, OrderID, ProductID, Quantity, UnitPrice) "
            "VALUES (?, ?, ?, ?, ?);",
            order_details,
        )

        conn.commit()

        print(f"Customers     : {len(customers):,}건")
        print(f"Products      : {len(products):,}건")
        print(f"Orders        : {len(orders):,}건")
        print(f"OrderDetails  : {len(order_details):,}건")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
