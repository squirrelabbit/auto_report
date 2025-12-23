import json
from konlpy.tag import Okt
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
import re
import os
from sklearn.feature_extraction.text import CountVectorizer

section = 'economy'
FILE_PATH = f'data/news_{section}_20251111.jsonl'
OUTPUT_FILE = f'output/topic_report_{section}_7000.json'
okt = Okt()

# 1. JSONL 파일에서 타이틀 데이터 추출
def load_titles_from_jsonl(file_path):
    titles = []
    # (이전 답변의 load_titles_from_jsonl 함수 내용을 여기에 복사하거나 사용)
    if not os.path.exists(file_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {file_path}")
        return titles

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if 'title' in data:
                    titles.append(data['title'])
            except json.JSONDecodeError:
                continue
    return titles

# 2. BERTopic을 사용한 토픽 모델링 및 분류
def generate_topics(titles):
    # 한국어에 적합한 Sentence Transformer 모델 로드
    # 'paraphrase-multilingual-MiniLM-L12-v2'는 다국어 및 한국어 문장 임베딩에 효과적입니다.
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    # 임베딩 생성
    embeddings = model.encode(titles, show_progress_bar=False)

    # BERTopic 모델 초기화 및 학습
    # vectorizer_model에 KoNLPy 형태소 분석기를 적용하여 한국어 명사 기반으로 토픽을 추출하도록 지정
    vectorizer = CountVectorizer(
        ngram_range=(1, 2),  # 단어 1~2개 조합을 키워드로 사용
        stop_words=None,
        tokenizer=lambda x: [word for word, tag in okt.pos(x, norm=True, stem=True) if tag in ['Noun', 'ProperNoun'] and len(word) > 1]
    )
    
    topic_model = BERTopic(
        language="multilingual",
        calculate_probabilities=True,
        verbose=False,
        vectorizer_model=vectorizer,
        nr_topics="5" # 토픽 개수를 자동으로 결정
    )

    topics, probs = topic_model.fit_transform(titles, embeddings)
    return topic_model, topics

def save_report_to_json(topic_model, titles, output_path, top_n=20):
    """BERTopic 결과를 JSON 파일로 저장합니다."""
    
    # 전체 토픽 정보 가져오기 (Count 기준 내림차순)
    topic_info = topic_model.get_topic_info().sort_values(by="Count", ascending=False)
    top_topics = topic_info[topic_info.Topic != -1].head(top_n)  # -1은 노이즈

    report_data = []
    
    for _, row in top_topics.iterrows():
        topic_id = int(row["Topic"])
        topic_name = row["Name"]
            
        topic_info = topic_model.get_topic(topic_id)
        
        # 토픽의 핵심 키워드 및 가중치
        topic_keywords = [{"word": word, "weight": weight} for word, weight in topic_info[:10]] # 상위 10개 키워드
        
        # 토픽의 대표 문서 (제목)
        representative_docs = topic_model.get_representative_docs(topic_id)
        
        # 해당 토픽에 속하는 모든 문서 제목
        indices = [i for i, t in enumerate(topic_model.topics_) if t == topic_id]
        all_docs_in_topic = [titles[i] for i in indices]
        
        # 토픽의 자동 생성된 이름 가져오기
        topic_name = topic_model.get_topic_info(topic_id)['Name'].iloc[0]

        topic_entry = {
            "topic_id": int(topic_id),
            "topic_name": topic_name,
            "core_keywords": topic_keywords,
            "representative_document": representative_docs[0] if representative_docs else "N/A",
            # "all_documents": all_docs_in_topic
        }
        report_data.append(topic_entry)

    # JSON 파일로 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        # ensure_ascii=False로 설정하여 한글이 깨지지 않도록 저장
        json.dump(report_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ 분석 결과가 성공적으로 '{output_path}' 파일에 저장되었습니다.")

# --- 실행 ---
if __name__ == "__main__":
    news_titles = load_titles_from_jsonl(FILE_PATH)

    if news_titles:
        topic_model, topics = generate_topics(news_titles)
        
        # JSON 파일로 저장 함수 호출
        save_report_to_json(topic_model, news_titles, OUTPUT_FILE)