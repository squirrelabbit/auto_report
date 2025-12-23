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

# --- 1. 설정 및 모델 정의 ---
FILE_PATH = 'data/news_economy_20251111.jsonl'
OUTPUT_FILE = 'daily_report_keywords_final.json'

# 1. 고성능 임베딩 모델 (KoSimCSE)
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"

# 2. 한국어 NER 모델 (KoELECTRA 기반)
NER_MODEL_NAME = "KPF/KPF-bert-ner" 
okt = Okt()

# 3. 고급 불용어 리스트 (분석 노이즈 제거)
ADVANCED_STOPWORDS = {
    '총리', '총영사', '모델', '성공', '만', '점', '판', '뒤흔든', '재조명', '길', '종합', '수', '것', '이', '그', '더', '우', '내',
    '기자', '단독', '발표', '관련', '뉴스', '오늘', '내일', '이슈', '주요', '속보', '말', '이야기', '조', '원', '명', '대', '속', '대한', 
    '의', '로', '에', '와', '과'
}

# --- 2. NER 모델 로딩 및 파이프라인 구축 ---
def setup_ner_pipeline():
    try:
        tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
        model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME)
        
        # 파이프라인 구축 (CPU/GPU 자동 감지)
        ner_pipe = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1 
        )
        print(f"✅ NER 모델 로드 완료: {NER_MODEL_NAME}")
        return ner_pipe
    except Exception as e:
        print(f"❌ NER 모델 로드 실패: {e}. (접근 오류, 이름 오류 등을 확인하세요)")
        return None

# --- 3. JSONL 데이터 로딩 ---
def load_titles_from_jsonl(file_path):
    # 예시 데이터 (파일이 없을 경우 사용)
    default_data = [
        {"title": "트럼프, 日총리 겨냥한 中총영사 ‘참수’ 극언에 “동맹이 우릴 더 이용”"},
        {"title": "감마, ‘3조원 더블 유니콘’ 등극…4년 만에 AI수익화 모델 성공"},
        {"title": "중국, '남중국해 갈등' 필리핀 대풍 피해 위로"},
        {"title": "가나, 英·남아공이 약탈한 유물 135점 돌려받아"},
        {"title": "\"핵심산업 화학·통신, 다 뺏길 판\"…중국 쫓아내는 유럽"},
        {"title": "美민주, 셧다운 종결 국면 내홍…슈머 원내대표 '교체론' 분출"},
        {"title": "튀르키예 프로축구 뒤흔든 '1000명 승부조작'…무리뉴 경고 재조명"},
        {"title": "Cho Kuk vows bold reform, public trust restoration in party leadership bid"},
        {"title": "'일본 총리 참수' 中 막말에도…트럼프 \"동맹이 우릴 더 이용\""},
        {"title": "\"조선통신사 길 되돌아보며 기뻤다\"…한일 자전거 대장정 완료(종합)"},
        {"title": "Iraq Election"}
    ]
    
    titles = []
    if not os.path.exists(file_path):
         print(f"경고: 파일을 찾을 수 없어 예시 데이터를 사용합니다. ({file_path}를 확인하세요.)")
         return [d['title'] for d in default_data]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if 'title' in data:
                    titles.append(data['title'])
            except json.JSONDecodeError:
                continue
    return titles

# --- 4. BERTopic 모델링 함수 (고성능 토크나이저 및 임베딩 적용) ---
def generate_topics_advanced(titles):
    print(f"🚀 고급 임베딩 모델 ({EMBEDDING_MODEL_NAME}) 로드 중...")
    
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME) 
    except Exception as e:
        print(f"❌ 임베딩 모델 로드 실패: {e}. 인터넷 연결 및 모델 이름을 확인하세요.")
        return None, None
        
    embeddings = model.encode(titles, show_progress_bar=False)
    
    # 고급 토크나이저 로직
    def advanced_tokenizer(text):
        tokens = []
        text = re.sub(r"[^\w\s]", "", text)
        
        if re.match(r"^[a-zA-Z0-9\s]+$", text.strip()):
            english_tokens = [w.lower().replace(' ', '_') for w in text.strip().split() if len(w) > 1 and w.lower() not in ADVANCED_STOPWORDS]
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

# --- 5. NER 분석 및 JSON 저장 함수 ---
def save_report_to_json_ner_integrated(topic_model, titles, output_path, ner_pipe):
    report_data = []
    sorted_topics = topic_model.get_topic_freq().sort_values('Count', ascending=False).Topic.tolist()
    
    for topic_id in sorted_topics:
        if topic_id == -1: continue
            
        representative_doc = topic_model.get_representative_docs(topic_id)[0]
        
        # 1. NER 모델로 대표 문서 분석
        ner_results = ner_pipe(representative_doc)
        
        # 2. 개체명 추출 및 필터링
        named_entities = []
        for entity in ner_results:
            entity_type = entity['entity'].split('-')[-1]
            named_entities.append({
                "entity": entity['word'].replace("##", ""), 
                "type": entity_type
            })

        topic_entry = {
            "topic_id": int(topic_id),
            "topic_size": int(topic_model.get_topic_freq().loc[topic_model.get_topic_freq()['Topic'] == topic_id, 'Count'].iloc[0]),
            "topic_name": topic_model.get_topic_info(topic_id)['Name'].iloc[0],
            "core_keywords": [{"word": w, "weight": round(wt, 4)} for w, wt in topic_model.get_topic(topic_id)[:5]],
            "representative_document": representative_doc,
            "extracted_entities": named_entities, 
        }
        report_data.append(topic_entry)

    # JSON 파일로 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ 고성능 NER 통합 분석 중간 결과가 '{output_path}' 파일에 저장되었습니다.")
    return report_data

# --- 6. LLM을 이용한 최종 보고서 텍스트 생성 ---
def generate_final_report_text(report_json_data):
    # LLM 클라이언트 초기화
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. LLM 보고서 생성을 건너뛰고 JSON 데이터만 출력합니다.")
        return None
    
    client = genai.Client(api_key=api_key)

    # 보고서 생성을 위한 시스템 지침 (Persona & Goal)
    system_prompt = (
        '''

        '''
    )
    
    json_string = json.dumps(report_json_data, ensure_ascii=False, indent=4)
    
    user_prompt = (
        f"다음 JSON 데이터를 분석하여, 요청된 '1. 국제 정세 및 외교/안보', "
        f"'2. 경제 및 산업', '3. 사회 및 기타'의 3대 분류에 맞춰 주제별 보고서 목록을 생성해 주세요. "
        f"출력은 오직 보고서 목록 텍스트로만 구성되어야 합니다.\n\nJSON 데이터:\n{json_string}"
    )

    try:
        print("\n⏳ LLM을 이용하여 최종 보고서 형식으로 변환 중... (API 호출)")
        config = GenerateContentConfig(
            system_instruction=system_prompt
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=user_prompt, # Contents는 사용자 프롬프트 텍스트만 전달
            config=config # config 객체 전달
        )
        return response.text
    except APIError as e:
        print(f"❌ Gemini API 호출 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        return None

# --- 7. 최종 실행 ---
if __name__ == "__main__":
    
    ner_pipeline = setup_ner_pipeline()
    news_titles = load_titles_from_jsonl(FILE_PATH)
    
    if news_titles and ner_pipeline:
        print("\n--- 토픽 모델링 시작 ---")
        topic_model, topics = generate_topics_advanced(news_titles)
        
        if topic_model:
            # 1. NER 통합 JSON 데이터 생성 및 저장
            report_json_data = save_report_to_json_ner_integrated(topic_model, news_titles, OUTPUT_FILE, ner_pipeline)

            # 2. LLM 호출하여 최종 보고서 텍스트 생성
            final_report_text = generate_final_report_text(report_json_data)
            
            if final_report_text:
                print("\n=======================================================")
                print("🏆 최종 일일 보고서 핵심 키워드 (LLM 재분류 결과)")
                print("=======================================================")
                print(final_report_text)
                print("=======================================================\n")
            
    elif not ner_pipeline:
        print("프로그램이 NER 모델 로드 문제로 종료됩니다.")
    else:
        print("분석할 타이틀 데이터가 없습니다.")