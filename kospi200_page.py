"""네이버 증권 국내 시장 페이지에서 코스피200 데이터를 크롤링한다 (BeautifulSoup4 + 페이징 처리)

대상 페이지: https://stock.naver.com/market/stock/kr

이 페이지는 자바스크립트가 화면을 그리기 때문에 requests로 받은 HTML에는 데이터 태그가 없다.
그래서 Selenium(헤드리스 브라우저)으로 화면을 완성한 뒤, 그 HTML을 BeautifulSoup4로 파싱한다.

수집 순서
  1) 시장 홈  /market/stock/kr
       지수 카드 a[data-nlogs^="home.nix"] -> 코스피200 지수(home.nixkospi200) 등 지수 14개
  2) 전체 종목 목록  /market/stock/kr/stocklist/capitalization  (코스피 선택, 시가총액순)
       한 번에 100행만 보이고 표 아래 '항목 더보기' 버튼으로 다음 100행을 불러온다(페이징).
       버튼이 사라질 때까지 반복해 코스피 전체(약 940행)를 모은 뒤 table > tbody > tr 을 파싱한다.
  3) 코스피200 편입종목 이름 목록 (m.stock.naver.com API)
       이 페이지에는 '코스피200' 필터가 없고 표에 소속 여부도 없으므로,
       편입종목 이름과 대조해 코스피200 종목만 골라낸다.

클래스명에 해시(예: ModulePriceNumber_price__MZ642)가 붙어 배포 때마다 바뀔 수 있으므로,
해시를 뺀 앞부분(ModulePriceNumber_price)만으로 태그를 찾는다.

사용법:
    pip install selenium beautifulsoup4 requests openpyxl
    python kospi200_page.py                     # 화면을 렌더링해서 수집 (Chrome)
    python kospi200_page.py --browser edge      # Edge 사용
    python kospi200_page.py --html home.html --list-html list.html   # 저장해 둔 HTML 파싱
결과: kospi200_page_indices.csv (지수), kospi200_page_stocks.csv (코스피200 종목)
"""
import argparse
import csv
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

HOME_URL = "https://stock.naver.com/market/stock/kr"
LIST_URL = "https://stock.naver.com/market/stock/kr/stocklist/capitalization?exchange=krx"
CONSTITUENTS_API = "https://m.stock.naver.com/api/index/KPI200/enrollStocks"

KOSPI200_CARD = 'a[data-nlogs="home.nixkospi200"]'
ROWS = "table tbody tr"
VIEW_MORE = '[class*="ViewMore_view-more-button__"] button'  # '항목 더보기'
MAX_CLICKS = 30          # 무한 반복 방지(코스피 약 940행 = 9회)

INDEX_FIELDS = ["코드", "이름", "현재값", "전일대비", "등락률(%)", "방향", "52주최고", "장상태"]
STOCK_FIELDS = ["순위", "코스피순위", "종목명", "현재가", "전일대비", "등락률(%)", "방향",
                "거래량", "거래대금(백만)", "고가", "저가", "시가총액"]
# 표 머리글 -> 결과 컬럼. 열 순서가 아니라 머리글 글자로 찾으므로 표 설정이 바뀌어도 안전하다.
HEADER_TO_FIELD = {"현재가": "현재가", "전일대비": "_change", "거래량": "거래량",
                   "거래대금": "거래대금(백만)", "고가": "고가", "저가": "저가", "시가총액": "시가총액"}


# ---------------------------------------------------------------- 렌더링 + 페이징
def render_pages(browser="chrome", timeout=30):
    """(시장 홈 HTML, 페이징으로 모두 불러온 코스피 목록 HTML)을 돌려준다."""
    from selenium import webdriver
    from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    if browser == "edge":
        opts, make = webdriver.EdgeOptions(), webdriver.Edge
    else:
        opts, make = webdriver.ChromeOptions(), webdriver.Chrome
    for arg in ("--headless=new", "--window-size=1400,1000", "--disable-gpu", "--lang=ko-KR", "--log-level=3"):
        opts.add_argument(arg)

    driver = make(options=opts)
    row_count = lambda: len(driver.find_elements(By.CSS_SELECTOR, ROWS))
    try:
        # 1) 시장 홈: 지수 카드가 그려질 때까지 대기
        driver.get(HOME_URL)
        WebDriverWait(driver, timeout).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, KOSPI200_CARD + ' [class*="ModulePriceNumber_price"]'))
        home_html = driver.page_source

        # 2) 전체 종목 목록: '코스피' 선택 후 '항목 더보기'를 끝까지 누른다
        driver.get(LIST_URL)
        WebDriverWait(driver, timeout).until(lambda d: row_count() > 0)
        chip = next(b for b in driver.find_elements(By.CSS_SELECTOR, '[class*="SelectButton_select-button__"]')
                    if b.text.strip() == "코스피")
        driver.execute_script("arguments[0].click()", chip)
        WebDriverWait(driver, timeout).until(lambda d: chip.get_attribute("aria-checked") == "true")
        time.sleep(1.5)  # 필터 적용 후 목록이 다시 그려질 시간

        for page in range(1, MAX_CLICKS + 1):
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, VIEW_MORE)
                if not buttons or not buttons[0].is_displayed():
                    break  # 버튼이 사라지면 마지막 페이지
                before = row_count()
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", buttons[0])
            except StaleElementReferenceException:
                break
            try:
                WebDriverWait(driver, timeout).until(lambda d: row_count() > before)
            except TimeoutException:
                break
            print(f"  더보기 {page}회: {row_count()}행")
        return home_html, driver.page_source
    finally:
        driver.quit()


# ---------------------------------------------------------------- 파싱 도구
def cls(el, name):
    """해시를 뺀 클래스명 앞부분으로 첫 번째 태그를 찾는다. (예: 'ModulePriceNumber_price')"""
    return el.find(class_=re.compile(rf"^{re.escape(name)}__")) if el else None


def text(el):
    return el.get_text(strip=True) if el else ""


def to_num(s):
    """'1,112.16' / '+2.01%' / '(-0.94%)' -> 숫자, 변환 불가이면 None"""
    m = re.search(r"[-+]?\d[\d,]*\.?\d*", s or "")
    if not m:
        return None
    v = float(m.group().replace(",", ""))
    return int(v) if v.is_integer() and "." not in m.group() else v


def parse_change(container):
    """ModulePriceChange 블록에서 (방향, 전일대비, 등락률)을 읽는다.

    방향은 화면 낭독용 a11y 태그('상승'/'하락'/'보합')에 들어 있고,
    전일대비 금액은 방향 없이 절댓값만 표시되므로 방향에 따라 부호를 붙인다.
    """
    amount = cls(container, "ModulePriceChange_amount")
    direction = ""
    if amount:
        a11y = amount.find(class_="a11y")
        direction = text(a11y)
        if a11y:
            a11y.extract()  # 금액 텍스트에서 '상승' 같은 글자를 뺀다
    diff = to_num(text(amount))
    sign = -1 if direction == "하락" else 1
    ratio = to_num(text(cls(container, "ModulePercent_module-percent")))
    return direction, (diff * sign if diff is not None else None), ratio


# ---------------------------------------------------------------- 지수 카드
def parse_index_cards(soup):
    rows = []
    for a in soup.select('a[data-nlogs^="home.nix"]'):
        parts = [p for p in a.get("href", "").split("/") if p]
        code = parts[-2] if len(parts) >= 2 else ""

        name = text(cls(a, "MarketStockInfo_stock-name")) or text(cls(a, "HomeIndicatorsKr_stock-name"))
        price = to_num(text(cls(cls(a, "MarketStockInfo_price-row") or a, "ModulePriceNumber_price")))
        direction, diff, ratio = parse_change(cls(a, "ModulePriceChange_module-price-change"))

        high = ""
        info = cls(a, "MarketStockInfo_stock-info")  # <span>52주 최고</span><span>1,518.11</span>
        if info:
            spans = info.find_all("span")
            if len(spans) >= 2:
                high = to_num(text(spans[1]))

        rows.append({
            "코드": code, "이름": name, "현재값": price, "전일대비": diff,
            "등락률(%)": ratio, "방향": direction, "52주최고": high,
            "장상태": text(cls(a, "ModuleMarketStatus_text")),
        })
    return rows


# ---------------------------------------------------------------- 종목 표
def parse_stock_table(soup):
    """종목 표(table)의 모든 행을 읽는다. 열은 머리글 글자로 찾는다."""
    table = soup.find("table", class_=re.compile(r"^Table_table__"))
    if not table:
        return []
    headers = [text(th) for th in table.select("thead th")]
    col = {h: i for i, h in enumerate(headers)}
    if "종목명" not in col:
        return []

    rows = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < len(headers):
            continue
        row = {"코스피순위": to_num(text(tr.find(class_="index"))),
               "종목명": text(cls(tds[col["종목명"]], "SingleLineText_text"))}
        for header, field in HEADER_TO_FIELD.items():
            if header not in col:
                continue
            td = tds[col[header]]
            if field == "_change":
                row["방향"], row["전일대비"], row["등락률(%)"] = parse_change(
                    cls(td, "ModulePriceChange_module-price-change"))
            elif field == "시가총액":
                row[field] = text(cls(td, "SingleLineText_text"))  # '1,596조 341억' 형태 그대로
            else:
                row[field] = to_num(text(cls(td, "SingleLinePrice_price")))
        rows.append(row)
    return rows


# ---------------------------------------------------------------- 코스피200 선별
def fetch_kospi200_names():
    """코스피200 편입종목 이름을 시가총액 순서대로 가져온다. (페이지 표에는 소속 정보가 없다)"""
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
    names, page = [], 1
    while True:
        resp = requests.get(CONSTITUENTS_API, params={"page": page, "pageSize": 50},
                            headers=headers, timeout=10)
        resp.raise_for_status()
        items = resp.json()
        names.extend(i["stockName"] for i in items)
        if len(items) < 50:
            return names
        page += 1
        time.sleep(0.5)


def select_kospi200(all_rows, names):
    """코스피 전체 행 중 편입종목 이름과 일치하는 행만 골라 코스피200 내 순위를 붙인다."""
    wanted = set(names)
    picked = [r for r in all_rows if r["종목명"] in wanted]
    picked.sort(key=lambda r: r["코스피순위"] or 0)
    for i, r in enumerate(picked, 1):
        r["순위"] = i
    missing = [n for n in names if n not in {r["종목명"] for r in picked}]
    return picked, missing


# ---------------------------------------------------------------- 출력/저장
def fmt(v, digits=0):
    return "-" if v is None or v == "" else f"{v:,.{digits}f}"


def save_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # 엑셀 한글 호환
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 한글 깨짐 방지

    ap = argparse.ArgumentParser(description="네이버 증권 코스피200 크롤러 (페이징)")
    ap.add_argument("--html", help="저장해 둔 시장 홈 HTML 파일 (--list-html 과 함께 사용)")
    ap.add_argument("--list-html", help="저장해 둔 종목 목록 HTML 파일 (모든 행을 불러온 상태)")
    ap.add_argument("--browser", choices=("chrome", "edge"), default="chrome", help="렌더링에 사용할 브라우저")
    ap.add_argument("-n", "--num", type=int, default=20, help="화면에 출력할 종목 수 (기본 20)")
    args = ap.parse_args()

    if args.html and args.list_html:
        with open(args.html, encoding="utf-8") as f:
            home_html = f.read()
        with open(args.list_html, encoding="utf-8") as f:
            list_html = f.read()
    elif args.html or args.list_html:
        sys.exit("--html 과 --list-html 은 함께 지정해야 합니다.")
    else:
        print("페이지를 렌더링하고 '항목 더보기'로 전체 목록을 불러오는 중...")
        try:
            home_html, list_html = render_pages(args.browser)
        except Exception as e:  # 브라우저/드라이버 문제, 시간 초과 등
            sys.exit(f"페이지를 렌더링하지 못했습니다: {type(e).__name__}: {str(e).splitlines()[0]}")

    indices = parse_index_cards(BeautifulSoup(home_html, "html.parser"))
    k200 = next((r for r in indices if r["코드"] == "KPI200"), None)
    if not k200:
        sys.exit("코스피200 지수 카드를 찾지 못했습니다. (페이지 구조가 바뀌었을 수 있습니다)")

    all_rows = parse_stock_table(BeautifulSoup(list_html, "html.parser"))
    if not all_rows:
        sys.exit("종목 표를 찾지 못했습니다. (페이지 구조가 바뀌었을 수 있습니다)")
    try:
        names = fetch_kospi200_names()
    except (requests.RequestException, ValueError, KeyError) as e:
        sys.exit(f"코스피200 편입종목 목록을 가져오지 못했습니다: {e}")
    stocks, missing = select_kospi200(all_rows, names)

    print(f"\n[{k200['이름']}] {fmt(k200['현재값'], 2)}  전일대비 {fmt(k200['전일대비'], 2)} "
          f"({fmt(k200['등락률(%)'], 2)}%) {k200['방향']}  52주 최고 {fmt(k200['52주최고'], 2)}")
    print(f"\n코스피 표 {len(all_rows)}행 중 코스피200 {len(stocks)}종목 (편입종목 목록 {len(names)}개)")
    for r in stocks[:args.num]:
        print(f"  {r['순위']:>3} {r['종목명']:<14.14} {fmt(r['현재가']):>10} {fmt(r['등락률(%)'], 2):>7}%  {r['시가총액']}")
    if len(stocks) > args.num:
        print(f"  ... (전체 {len(stocks)}개는 CSV에 저장)")
    if missing:
        print(f"\n※ 표에서 이름이 일치하지 않아 빠진 편입종목 {len(missing)}개: {', '.join(missing)}")

    save_csv("kospi200_page_indices.csv", INDEX_FIELDS, indices)
    save_csv("kospi200_page_stocks.csv", STOCK_FIELDS, stocks)
    print("\n저장 완료: kospi200_page_indices.csv, kospi200_page_stocks.csv")


if __name__ == "__main__":
    main()
