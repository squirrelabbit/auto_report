import json
import os
from google import genai
from google.genai.errors import APIError
from google.genai.types import GenerateContentConfig # LLM 설정 객체 임포트

# --- 1. LLM API 호출 함수 (이전 코드에서 수정된 버전) ---
def generate_final_report_text(report_json_data):
    """
    NER/BERTopic 분석 결과를 LLM에 입력하여 최종 보고서 형식으로 변환합니다.
    """
    # LLM 클라이언트 초기화
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ GEMINI_API_KEY 환경 변수가 설정되지 않아 LLM 호출을 건너뛰었습니다."
    
    client = genai.Client(api_key=api_key)

    # 보고서 생성을 위한 시스템 지침
    system_prompt = (
        "You are an expert geopolitical and economic analyst specializing in daily news reporting. "
        "Your task is to analyze the provided structured JSON data and transform it into a highly structured, categorized key summary report, "
        "exactly matching the user's requested Korean format. "
        "Strictly adhere to the following three major sections in your final output. Do not use any introductory or concluding remarks: "
        "1. 국제 정세 및 외교/안보"
        "2. 경제 및 산업"
        "3. 사회 및 기타"
        "Under each major category, create clear sub-categories (e.g., '미국 정치', '중국 관련', '첨단 산업') based on the content of the topics. "
        "Each final line must be a concise, high-value summary of the topic/document, utilizing the keywords and entities found."
    )
    
    json_string = json.dumps(report_json_data, ensure_ascii=False, indent=4)
    
    user_prompt = (
        f"다음 JSON 데이터를 분석하여, 요청된 '1. 국제 정세 및 외교/안보', '2. 경제 및 산업', '3. 사회 및 기타'의 3대 분류에 맞춰 주제별 보고서 목록을 생성해 주세요. "
        f"출력은 오직 보고서 목록 텍스트로만 구성되어야 합니다.\n\nJSON 데이터:\n{json_string}"
    )

    try:
        print("\n⏳ LLM을 이용하여 최종 보고서 형식으로 변환 중... (API 호출)")
        
        # System Instruction을 config 객체에 넣어 전달
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
        return f"❌ Gemini API 호출 오류: {e}"
    except Exception as e:
        return f"❌ 예상치 못한 오류 발생: {e}"

# --- 2. 시뮬레이션용 JSON 데이터 (NER/BERTopic 결과) ---
SIMULATED_JSON_DATA = [
    {
        "topic_id": 0,
        "topic_size": 3,
        "topic_name": "0_트럼프_참수_동맹_이용",
        "core_keywords": [{"word": "트럼프", "weight": 0.051}, {"word": "참수", "weight": 0.045}, {"word": "동맹", "weight": 0.038}, {"word": "中", "weight": 0.030}],
        "representative_document": "트럼프, 日총리 겨냥한 中총영사 ‘참수’ 극언에 “동맹이 우릴 더 이용”",
        "extracted_entities": [{"entity": "트럼프", "type": "PER"}, {"entity": "日", "type": "LOC"}, {"entity": "총영사", "type": "POH"}, {"entity": "中", "type": "LOC"}]
    },
    {
        "topic_id": 1,
        "topic_size": 2,
        "topic_name": "1_AI_유니콘_감마",
        "core_keywords": [{"word": "감마", "weight": 0.060}, {"word": "유니콘", "weight": 0.055}, {"word": "AI", "weight": 0.050}, {"word": "수익화", "weight": 0.042}],
        "representative_document": "감마, ‘3조원 더블 유니콘’ 등극…4년 만에 AI수익화 모델 성공",
        "extracted_entities": [{"entity": "감마", "type": "ORG"}, {"entity": "3조원", "type": "NOH"}, {"entity": "AI", "type": "ORG"}]
    },
    {
        "topic_id": 2,
        "topic_size": 3,
        "topic_name": "2_유럽_중국_화학_통신_갈등",
        "core_keywords": [{"word": "중국", "weight": 0.058}, {"word": "유럽", "weight": 0.055}, {"word": "화학", "weight": 0.040}, {"word": "통신", "weight": 0.040}],
        "representative_document": "\"핵심산업 화학·통신, 다 뺏길 판\"…중국 쫓아내는 유럽",
        "extracted_entities": [{"entity": "화학", "type": "ORG"}, {"entity": "통신", "type": "ORG"}, {"entity": "중국", "type": "LOC"}, {"entity": "유럽", "type": "LOC"}]
    },
    {
        "topic_id": 3,
        "topic_size": 3,
        "topic_name": "3_민주당_조국_선거",
        "core_keywords": [{"word": "민주", "weight": 0.045}, {"word": "내홍", "weight": 0.040}, {"word": "조국", "weight": 0.035}, {"word": "셧다운", "weight": 0.030}],
        "representative_document": "美민주, 셧다운 종결 국면 내홍…슈머 원내대표 '교체론' 분출",
        "extracted_entities": [{"entity": "美민주", "type": "ORG"}, {"entity": "셧다운", "type": "EVT"}, {"entity": "슈머", "type": "PER"}, {"entity": "조국", "type": "PER"}]
    },
    {
        "topic_id": 4,
        "topic_size": 2,
        "topic_name": "4_유물_승부조작",
        "core_keywords": [{"word": "유물", "weight": 0.055}, {"word": "가나", "weight": 0.050}, {"word": "승부조작", "weight": 0.045}, {"word": "튀르키예", "weight": 0.040}],
        "representative_document": "가나, 英·남아공이 약탈한 유물 135점 돌려받아",
        "extracted_entities": [{"entity": "가나", "type": "LOC"}, {"entity": "英", "type": "LOC"}, {"entity": "남아공", "type": "LOC"}, {"entity": "유물", "type": "NOH"}]
    }
]

# --- 3. 테스트 실행 ---
if __name__ == "__main__":
    
    print("=======================================================")
    print("📝 최종 보고서 형식 변환 테스트 (LLM 호출)")
    print("=======================================================")
    
    final_report_text = generate_final_report_text(SIMULATED_JSON_DATA)
    
    print("\n[LLM 생성 결과]")
    print("-------------------------------------------------------")
    print(final_report_text)
    print("-------------------------------------------------------")
    print("=======================================================\n")