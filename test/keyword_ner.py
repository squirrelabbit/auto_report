import json
import re
import os
import torch
from konlpy.tag import Okt
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from google import genai
from google.genai.errors import APIError
from google.genai.types import GenerateContentConfig # LLM 설정 객체 임포트
from datetime import datetime

# --- 설정 (Constants) ---
section = 'society'
FILE_PATH = f'data/news_{section}_20251111.jsonl'
OUTPUT_FILE = f'topic_report_{section}.json'
okt = Okt()

# 1. 불용어 리스트
ADVANCED_STOPWORDS = {
    '총리', '총영사', '모델', '성공', '만', '점', '판', '뒤흔든', '재조명', '길', '종합', '수', '것', '이', '그', '더', '우', '내',
    '기자', '단독', '발표', '관련', '뉴스', '오늘', '내일', '이슈', '주요', '속보', '말', '이야기', '조', '원', '명', '대', '속', '대한'
}

# --- 0. NER 모델 로딩 및 파이프라인 구축 ---
# 한국어 NER 모델 로드: Koelectra 기반 모델 사용
NER_MODEL_NAME = "KPF/KPF-bert-ner"
try:
    # 파이프라인 구축 (CPU/GPU 자동 감지)
    ner_pipeline = pipeline(
        "ner",
        model=AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME),
        tokenizer=AutoTokenizer.from_pretrained(NER_MODEL_NAME),
        device=0 if torch.cuda.is_available() else -1 # GPU 사용 가능 시 0, 아니면 -1 (CPU)
    )
    print(f"✅ NER 모델 로드 완료: {NER_MODEL_NAME}")
except Exception as e:
    print(f"❌ NER 모델 로드 실패: {e}")
    ner_pipeline = None

# --- JSONL 데이터 로딩 (이전과 동일) ---
def load_titles_from_jsonl(file_path):
    # 예시 데이터 (실제 사용 시 파일을 읽는 로직으로 대체)
    if not os.path.exists(file_path):
         print("해당파일이 존재하지 않습니다")
         return 
    titles = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if 'title' in data:
                    titles.append(data['title'])
            except json.JSONDecodeError:
                continue
    return titles

# --- BERTopic 모델링 함수 (이전과 동일) ---
def generate_topics_advanced(titles):
    print("🚀 임베딩 모델 (Ko-SBERT) 로드 중...")
    model = SentenceTransformer("BM-K/KoSimCSE-roberta") 
    embeddings = model.encode(titles, show_progress_bar=False)
    
    def advanced_tokenizer(text):
        # (불용어, 길이 필터링 포함된 토크나이징 로직)
        tokens = []
        text = re.sub(r"[^\w\s]", "", text)
        if re.match(r"^[a-zA-Z0-9\s]+$", text.strip()):
            english_tokens = [w.lower() for w in text.strip().split() if len(w) > 1 and w.lower() not in ADVANCED_STOPWORDS]
            tokens.extend(english_tokens)
        else:
            for word, tag in okt.pos(text, norm=True, stem=True):
                is_noun = tag in ['Noun', 'ProperNoun']
                is_meaningful_length = len(word) > 1 or word in ['日', '中', '美', '英']
                is_not_stopword = word not in ADVANCED_STOPWORDS
                if is_noun and is_meaningful_length and is_not_stopword and not word.isdigit():
                    tokens.append(word)
        return tokens

    vectorizer = CountVectorizer(
        ngram_range=(1, 2),
        tokenizer=advanced_tokenizer
    )
    
    topic_model = BERTopic(
        language="multilingual",
        calculate_probabilities=True,
        verbose=False,
        vectorizer_model=vectorizer,
        nr_topics="auto",
        min_topic_size=2
    )

    topics, probs = topic_model.fit_transform(titles, embeddings)
    return topic_model, topics

# --- 2. NER 분석 및 결과 저장 함수 (핵심 변경) ---
def save_report_to_json_ner_integrated(topic_model, titles, output_path, ner_pipe):
    """
    NER 모델 분석 결과를 통합하여 구조화된 JSON 파일로 저장
    """
    if not ner_pipe:
        print("❌ NER 파이프라인이 로드되지 않아, NER 분석을 건너뜁니다.")
        return

    report_data = []
    sorted_topics = topic_model.get_topic_freq().sort_values('Count', ascending=False).Topic.tolist()
    
    for topic_id in sorted_topics:
        if topic_id == -1: # 노이즈 토픽 제외
            continue
            
        topic_name = topic_model.get_topic_info(topic_id)['Name'].iloc[0]
        representative_doc = topic_model.get_representative_docs(topic_id)[0]
        
        # 🚨 대표 문서를 NER 모델로 분석
        ner_results = ner_pipe(representative_doc)
        
        # 개체명 추출 및 필터링
        named_entities = []
        for entity in ner_results:
            # NER 태그 유형 매핑 (PER: 인물, LOC: 위치/국가, ORG: 조직/기관, DAT/TIM: 날짜/시간, POH/NOH: 직책/기타)
            entity_type = entity['entity'].split('-')[-1] # B-PER -> PER, I-PER -> PER
            named_entities.append({
                "entity": entity['word'].replace("##", ""), # KoELECTRA 토크나이저의 잔여물 제거
                "type": entity_type
            })

        topic_entry = {
            "topic_id": int(topic_id),
            "topic_name": topic_name,
            "representative_document": representative_doc,
            "extracted_entities": named_entities, # NER 결과 통합
            "core_keywords": [{"word": w, "weight": round(wt, 4)} for w, wt in topic_model.get_topic(topic_id)[:5]],
            "topic_size": int(topic_model.get_topic_freq().loc[topic_model.get_topic_freq()['Topic'] == topic_id, 'Count'].iloc[0])
        }
        report_data.append(topic_entry)
        
    final_output = {
        "total_count": len(titles),   # 전체 뉴스 데이터 건수
        "topic_count": len(report_data),  # 토픽 개수(optional)
        "topics": report_data
    }

    # JSON 파일로 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ NER 통합 분석 결과가 '{output_path}' 파일에 저장되었습니다.")


# --- 7. 최종 실행 ---
if __name__ == "__main__":
    start = datetime.now()
    news_titles = load_titles_from_jsonl(FILE_PATH)
    
    if news_titles and ner_pipeline:
        print("\n--- 토픽 모델링 시작 ---")
        topic_model, topics = generate_topics_advanced(news_titles)
        
        if topic_model:
            # 1. NER 통합 JSON 데이터 생성 및 저장
            report_json_data = save_report_to_json_ner_integrated(topic_model, news_titles, OUTPUT_FILE, ner_pipeline)

            # 2. LLM 호출하여 최종 보고서 텍스트 생성

    elif not ner_pipeline:
        print("프로그램이 NER 모델 로드 문제로 종료됩니다.")
    else:
        print("분석할 타이틀 데이터가 없습니다.")

    
    end = datetime.now()
    print("걸린 시간:", end - start)
