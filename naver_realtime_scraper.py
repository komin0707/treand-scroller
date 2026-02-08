#!/usr/bin/env python3
"""NAVER realtime-like scraper using Selenium.

Usage:
  python3 naver_realtime_scraper.py
  python3 naver_realtime_scraper.py --json
  python3 naver_realtime_scraper.py --no-headless
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from collections import Counter
from typing import Iterable

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print(
        "필수 모듈이 없습니다. 설치: python3 -m pip install beautifulsoup4 selenium",
        file=sys.stderr,
    )
    raise

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException, TimeoutException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
except ModuleNotFoundError:
    print(
        "필수 모듈이 없습니다. 설치: python3 -m pip install selenium webdriver-manager",
        file=sys.stderr,
    )
    raise

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ModuleNotFoundError:
    print(
        "필수 모듈이 없습니다. 설치: python3 -m pip install webdriver-manager",
        file=sys.stderr,
    )
    raise


def unique_top(values: Iterable[str], limit: int = 10) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        t = re.sub(r"\s+", " ", str(v or "")).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def normalize_article_href(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        return f"https://news.naver.com{href}"
    return f"https://news.naver.com/{href}"


def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(20)
    return driver


def wait_dom_ready(driver: webdriver.Chrome, timeout: int = 12) -> None:
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def scrape_realtime_keywords(driver: webdriver.Chrome) -> list[str]:
    # 요청하신 방식: Google Trends 페이지를 Selenium으로 렌더링 후 키워드 추출
    url = "https://trends.google.com/trending?geo=KR&hours=4"
    try:
        driver.get(url)
        wait_dom_ready(driver)
        time.sleep(5)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        table_body = soup.find("tbody", attrs={"jsname": "cC57zf"})
        if not table_body:
            return []

        rows = table_body.find_all("tr")
        if not rows:
            return []

        raw: list[str] = []
        for row in rows:
            keyword_div = row.find("div", class_="mZ3RIc")
            if keyword_div:
                raw.append(keyword_div.get_text(strip=True))
        return unique_top(raw, 10)
    except (TimeoutException, WebDriverException):
        return []


def scrape_popular_articles(driver: webdriver.Chrome) -> list[dict[str, str]]:
    urls = [
        "https://news.naver.com/main/ranking/popularDay.naver",
        "https://news.naver.com/main/ranking/popularDay.naver?mid=etc&sid1=111",
    ]

    selectors = [
        ".rankingnews_list .list_title",
        ".rankingnews_list a[href*='/article/']",
        ".rankingnews_box a[href*='/article/']",
        ".rankingnews_list li a",
        ".rankingnews_box li a",
    ]

    for url in urls:
        try:
            driver.get(url)
            wait_dom_ready(driver)
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            raw: list[dict[str, str]] = []
            for sel in selectors:
                for a in soup.select(sel):
                    title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
                    href = normalize_article_href(a.get("href", ""))
                    if len(title) < 4:
                        continue
                    if "/article/" not in href:
                        continue
                    raw.append({"title": title, "href": href})

            dedup: list[dict[str, str]] = []
            seen: set[tuple[str, str]] = set()
            for item in raw:
                key = (item["title"], item["href"])
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(item)
                if len(dedup) >= 10:
                    return dedup
        except (TimeoutException, WebDriverException):
            continue

    return []


def derive_keywords_from_articles(articles: list[dict[str, str]]) -> list[str]:
    stop = {
        "기자",
        "뉴스",
        "오늘",
        "정부",
        "시장",
        "한국",
        "속보",
        "관련",
        "대한",
    }
    c = Counter()
    for a in articles:
        words = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", a.get("title", "")).split()
        for w in words:
            w = w.strip()
            if len(w) < 2 or w in stop:
                continue
            c[w] += 1
    return [w for w, _ in c.most_common(10)]


def collect(headless: bool = True) -> dict:
    warnings: list[str] = []
    keywords: list[str] = []
    articles: list[dict[str, str]] = []

    try:
        driver = build_driver(headless=headless)
    except WebDriverException as e:
        return {
            "keywords": [],
            "articles": [],
            "warnings": [
                "Chrome WebDriver 실행 실패: " + str(e),
                "Chrome 설치 또는 Selenium Manager 네트워크 접근 상태를 확인하세요.",
            ],
        }

    try:
        keywords = scrape_realtime_keywords(driver)
        articles = scrape_popular_articles(driver)
    finally:
        driver.quit()

    if not keywords:
        alt = derive_keywords_from_articles(articles)
        if alt:
            keywords = alt
            warnings.append("실시간 검색어 원본 수집 실패로 기사 제목 기반 키워드로 대체했습니다.")
        else:
            warnings.append("실시간 검색어를 생성하지 못했습니다.")

    if not articles:
        warnings.append("실시간 인기기사 수집에 실패했습니다.")

    return {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "keywords": keywords[:10],
        "articles": articles[:10],
        "warnings": warnings,
    }


def print_text(data: dict) -> None:
    print("[실시간 검색어 TOP 10]")
    for i, k in enumerate(data["keywords"], 1):
        print(f"{i}. {k}")

    print("\n[실시간 인기기사 TOP 10]")
    for i, a in enumerate(data["articles"], 1):
        print(f"{i}. {a['title']}")
        print(f"   {a['href']}")

    if data["warnings"]:
        print("\n[주의]")
        for w in data["warnings"]:
            print(f"- {w}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--no-headless", action="store_true", help="브라우저 창 표시")
    parser.add_argument("--out", type=str, default="", help="결과 JSON 파일 경로")
    args = parser.parse_args()

    data = collect(headless=not args.no_headless)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_text(data)


if __name__ == "__main__":
    main()
