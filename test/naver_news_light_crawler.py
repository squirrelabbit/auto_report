# crawl_package/modules/naver_news_full_crawler.py
import aiohttp
import asyncio
import json
from bs4 import BeautifulSoup
from datetime import datetime
import os

BASE_URL = "https://news.naver.com/main/list.naver"

SECTIONS = {
    "politics": 100,
    "economy": 101,
    "society": 102,
    "life_culture": 103,
    "world": 104,
    "it_science": 105,
}

# -------------------------------------------------------
# 🟦 1) 기사 본문 + 날짜 수집 함수
# -------------------------------------------------------
async def fetch_article_detail(session, url):
    try:
        async with session.get(url) as resp:
            html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")

        # -----------------------------
        # 1) 본문
        # -----------------------------
        body = soup.select_one("#dic_area")
        body_text = body.get_text("\n", strip=True) if body else ""


        # -----------------------------
        # 2) 날짜(JSON-LD 기반)
        # -----------------------------
        published_at = ""
        modified_at = ""

        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                data = json.loads(json_ld.string)

                # 표준 JSON-LD 스키마 기반
                published_at = data.get("datePublished", "")
                modified_at = data.get("dateModified", "")
            except:
                pass

        # fallback (혹시 JSON-LD 없는 특수 기사)
        if not published_at:
            date_tag = soup.select_one("span.media_end_head_info_datestamp_time")
            if date_tag and date_tag.has_attr("data-date-time"):
                published_at = date_tag["data-date-time"]

        # -----------------------------
        # 3) 기자명
        # -----------------------------
        reporter_tag = soup.select_one(".media_end_head_journalist_name")
        reporter = reporter_tag.get_text(strip=True) if reporter_tag else ""

        return {
            "content": body_text,
            "published_at": published_at,
            "modified_at": modified_at,
            "reporter": reporter
        }

    except Exception as e:
        return {
            "content": "",
            "published_at": "",
            "modified_at": "",
            "reporter": "",
            "error": str(e)
        }

# -------------------------------------------------------
# 🟦 2) 리스트 페이지 수집 (제목/요약/언론사/URL)
# -------------------------------------------------------
async def fetch_section_page(session, sid1, page, date_str):
    params = {
        "mode": "LSD",
        "mid": "mid",
        "sid1": sid1,
        "date": date_str,
        "page": page,
    }
    async with session.get(BASE_URL, params=params) as resp:
        html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("ul.type06_headline li dl") or soup.select("ul.type06 li dl")
    results = []

    for art in articles:
        title_tag = art.select_one("dt:not(.photo) a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag["href"]

        summary_tag = art.select_one("dd.lede")
        summary = summary_tag.get_text(strip=True) if summary_tag else ""

        press_tag = art.select_one("dd.writing")
        press = press_tag.get_text(strip=True) if press_tag else ""

        results.append({
            "title": title,
            "summary": summary,
            "press": press,
            "url": link,
            "section_code": sid1,
            "page": page,
            "collected_at": datetime.now().isoformat(),
        })

    return results


# -------------------------------------------------------
# 🟦 3) 해당 섹션 전체 수집 + 본문 병렬 처리
# -------------------------------------------------------
async def fetch_section_all(session, section_name, sid1, date_str, output_dir):
    all_articles = []

    # 리스트 반복 수집
    for page in range(1, 50):
        items = await fetch_section_page(session, sid1, page, date_str)
        if not items:
            break
        all_articles.extend(items)
        await asyncio.sleep(0.3)

    # ⬇️ 본문 병렬 수집
    detail_tasks = [
        fetch_article_detail(session, item["url"]) for item in all_articles
    ]
    details = await asyncio.gather(*detail_tasks)

    # 리스트 + 본문 merge
    for i, detail in enumerate(details):
        all_articles[i].update(detail)

    # 파일 저장
    if all_articles:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"news_{section_name}_{date_str}.jsonl")

        with open(output_path, "w", encoding="utf-8") as f:
            for item in all_articles:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        print(f"✅ [{section_name}] {len(all_articles)}건 저장 완료 → {output_path}")
    else:
        print(f"⚠️ [{section_name}] 수집된 뉴스 없음.")


# -------------------------------------------------------
# 🟦 4) 전체 섹션 병렬 실행
# -------------------------------------------------------
async def crawl_full_today_by_section():
    today_str = datetime.now().strftime("%Y%m%d")
    output_dir = "output"

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_section_all(session, name, sid, today_str, output_dir)
            for name, sid in SECTIONS.items()
        ]
        await asyncio.gather(*tasks)

    print(f"\n🎯 모든 섹션 수집 완료 ({today_str})")


if __name__ == "__main__":
    asyncio.run(crawl_full_today_by_section())
