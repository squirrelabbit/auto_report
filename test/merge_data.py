import json
import os
from tqdm import tqdm

# 폴더 경로 (각 개별 JSON이 있는 곳)
section = "society"
INPUT_DIR = f"data/raw_data_{section}"
OUTPUT_PATH = f"data/news_{section}_20251111.jsonl"

os.makedirs("output", exist_ok=True)

# ------------------------------------------
# source → category 자동 매핑 함수
# ------------------------------------------
def map_category(source_text: str) -> str:
    if not source_text:
        return "others"
    text = source_text.lower()
    if "정치" in text:
        return "politics"
    if "경제" in text or "금융" in text:
        return "economy"
    if "사회" in text:
        return "society"
    if "생활" in text or "문화" in text:
        return "life"
    if "세계" in text or "국제" in text:
        return "world"
    if "it" in text or "과학" in text or "기술" in text:
        return "it"
    return "others"


# ------------------------------------------
# 개별 파일 → 표준화 변환 함수
# ------------------------------------------
def transform_record(rec):
    return {
        "title": rec.get("doc_title", "").strip(),
        "summary": rec.get("doc_content", "").strip(),
        "press": rec.get("media", "").strip(),
        "url": rec.get("doc_url", "").strip(),
        "category": 'economy',
        "collected_at": rec.get("doc_datetime", "")
    }


# ------------------------------------------
# 메인 실행
# ------------------------------------------
with open(OUTPUT_PATH, "w", encoding="utf-8") as out_f:
    for filename in tqdm(os.listdir(INPUT_DIR), desc="Merging JSON files"):
        if not filename.endswith(".json"):
            continue
        file_path = os.path.join(INPUT_DIR, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                rec = json.load(f)
            merged = transform_record(rec)
            out_f.write(json.dumps(merged, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ {filename} 처리 실패: {e}")

print(f"\n✅ 변환 완료: {OUTPUT_PATH}")
