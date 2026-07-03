# auto_report

온라인 뉴스·댓글 데이터를 바탕으로 일일 여론 보고서를 자동 생성하는 Python 기반 프로젝트입니다.  
한국어 텍스트 전처리, 이슈 요약용 데이터 구조화, HTML 템플릿 렌더링, PDF 문서 생성까지 하나의 흐름으로 연결하는 데 초점을 맞췄습니다.

> 단순한 분석 스크립트가 아니라, 비정형 텍스트를 사람이 읽는 보고서 형태로 바꾸는 자동화 파이프라인을 구현한 프로젝트입니다.

## 프로젝트 한눈에 보기

- 온라인 이슈 데이터를 정리해 일일 보고서 형태로 자동 산출합니다.
- `report-ready JSON` 스키마를 중심으로 데이터 가공 단계와 출력 단계를 분리했습니다.
- 최종 산출물은 HTML 기반 레이아웃을 거쳐 PDF로 생성됩니다.
- 별도 실험 코드로 뉴스 수집, 한국어 전처리, 중복 제거, BERTopic/NER/LLM 기반 주제 분류를 검증했습니다.

## 왜 만들었는가

온라인 여론 보고서는 보통 기사, 커뮤니티, 댓글 데이터를 사람이 일일이 읽고 정리한 뒤 문서로 다시 편집하는 방식으로 만들어집니다.  
이 프로젝트는 그 과정을 아래와 같이 줄이는 것을 목표로 했습니다.

- 여러 소스에서 나온 텍스트를 일정한 구조로 정리
- 반복적으로 등장하는 중복 기사·댓글 제거
- 보고서에 바로 넣을 수 있는 JSON 스키마로 변환
- 템플릿 기반으로 일관된 문서 레이아웃 생성
- 최종 결과물을 PDF로 자동 출력

## 핵심 흐름

```mermaid
flowchart LR
    A["뉴스 / 커뮤니티 / 댓글 데이터"] --> B["수집 및 필터링"]
    B --> C["인기순위 산정"]
    C --> D["한국어 전처리 / 중복 제거"]
    D --> E["토픽 / 개체명 / 요약 실험"]
    C --> F["Report-ready JSON 조립"]
    E -. 선택적 확장 .-> F
    F --> G["Jinja2 HTML 렌더링"]
    G --> H["WeasyPrint PDF 생성"]
```

## 구현 범위

| 영역 | 현재 상태 | 설명 |
| --- | --- | --- |
| 리포트 조립 | 구현됨 | `processed_rows`를 보고서용 JSON 구조로 변환 |
| 필드 검증 | 구현됨 | 필수 필드와 섹션 구조 검증 |
| HTML 렌더링 | 구현됨 | Jinja2 템플릿 기반 보고서 생성 |
| PDF 생성 | 구현됨 | WeasyPrint로 최종 PDF 출력 |
| 한국어 전처리 | 구현됨 | 불용어 제거, 형태소 기반 토큰화, 기본형 보정 |
| 중복 제거 | 구현됨 | SimHash + MinHash 조합으로 유사 문서 제거 |
| 뉴스 수집 | 실험 | 네이버 뉴스 섹션 단위 비동기 수집 스크립트 |
| 토픽/NER/LLM | 실험 | BERTopic, NER, Gemini 기반 분류/요약 검증 |

## 이 프로젝트가 보여주는 역량

- 비정형 텍스트를 리포트 스키마로 구조화하는 데이터 파이프라인 설계
- 한국어 형태소 처리와 중복 제거를 통한 텍스트 정제
- 분석 결과를 문서 산출물까지 연결하는 자동화 설계
- 실험 코드와 문서 출력 코어를 분리해 확장 가능하게 구성한 구조화 역량

## 기술 스택

### Core

- Python
- Jinja2
- WeasyPrint

### Data / NLP

- pandas
- BeautifulSoup
- requests / aiohttp
- KoNLPy (`Okt`)
- Kiwi
- simhash
- datasketch (`MinHash`, `MinHashLSH`)

### Topic / LLM Experiments

- BERTopic
- sentence-transformers
- transformers
- Google GenAI (Gemini)
- PyTorch

## 디렉토리 구조

```text
auto_report/
├─ src/
│  ├─ main.py
│  ├─ sample_data.json
│  ├─ daily_report.pdf
│  ├─ report_ready/
│  │  ├─ assemble.py
│  │  └─ validate_fields.py
│  ├─ pdf_generator/
│  │  ├─ render_html.py
│  │  └─ generate_pdf.py
│  └─ report_templates/
│     ├─ daily.html
│     └─ report.css
├─ summarize/
│  ├─ summary_collectiong.py
│  ├─ summary_preprocessing.py
│  ├─ summary_executing.py
│  └─ purity_comment.py
└─ test/
   ├─ naver_news_light_crawler.py
   ├─ keyword_ner.py
   ├─ llm_generate.py
   └─ 기타 실험 스크립트 / 샘플 데이터
```

## 빠른 실행

현재 저장소에서 가장 바로 확인 가능한 데모는 `sample_data.json`을 사용한 PDF 생성입니다.  
스크립트가 상대 경로를 사용하므로 `src/` 디렉토리에서 실행하는 것을 기준으로 합니다.

### 1. 가상환경 생성

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 코어 의존성 설치

```bash
pip install jinja2 weasyprint
```

참고:
- WeasyPrint는 운영체제에 따라 `cairo`, `pango` 같은 시스템 라이브러리가 추가로 필요할 수 있습니다.
- `summarize/`, `test/` 아래 실험 스크립트까지 실행하려면 NLP/ML 관련 패키지를 별도로 더 설치해야 합니다.

### 3. 샘플 리포트 생성

```bash
cd src
python3 main.py
```

생성 결과:

- 출력 파일: `src/daily_report.pdf`

## 입력 데이터 예시

리포트 렌더링 코어는 아래와 같은 구조의 JSON을 입력으로 받습니다.

```json
{
  "report_title": "온라인 일일 여론 종합",
  "report_date": "2025-11-03",
  "report_unit": "국민소통실",
  "top_news_topics": [],
  "top_sns_keywords": [],
  "media_top_issues": [],
  "sections": [
    {
      "section_name": "대통령실",
      "issues": [
        {
          "issue": "한중 정상회담",
          "issue_summary": "이슈 요약",
          "top_posts": [],
          "reactions": []
        }
      ]
    }
  ]
}
```

이 구조는 다음 순서로 사용됩니다.

1. `src/report_ready/assemble.py`에서 보고서용 JSON 조립
2. `src/report_ready/validate_fields.py`에서 필수 필드 검증
3. `src/pdf_generator/render_html.py`에서 HTML 렌더링
4. `src/pdf_generator/generate_pdf.py`에서 PDF 생성

## 주요 파일 설명

| 파일 | 역할 |
| --- | --- |
| `src/api.py` | FastAPI 기반 보고서 생성 API (검증·렌더링·PDF를 HTTP로 제공) |
| `src/report_ready/assemble.py` | 처리된 레코드를 섹션 중심 보고서 JSON으로 변환 |
| `src/report_ready/validate_fields.py` | 템플릿 렌더링 전 스키마 검증 |
| `src/pdf_generator/render_html.py` | Jinja2 템플릿 로딩 및 HTML 렌더링 |
| `src/pdf_generator/generate_pdf.py` | HTML을 PDF로 변환 |
| `src/report_templates/daily.html` | 일일 리포트 템플릿 |
| `summarize/summary_preprocessing.py` | 한국어 전처리 및 중복 제거 파이프라인 |
| `summarize/purity_comment.py` | 댓글 군집 정리 및 요약 입력 데이터 준비 |
| `test/naver_news_light_crawler.py` | 뉴스 기사 수집 실험 |
| `test/keyword_ner.py`, `test/llm_generate.py` | 토픽 추출, NER, LLM 분류 실험 |

## FastAPI 보고서 API

배치 실행(`main.py`) 외에, 같은 파이프라인을 HTTP API로 호출할 수 있습니다.

```bash
pip install -r requirements.txt
cd src
uvicorn api:app --reload
```

| 메서드 | 경로 | 역할 |
| --- | --- | --- |
| `GET` | `/health` | 서비스 상태 확인 |
| `POST` | `/reports/validate` | report-ready JSON 스키마 검증 |
| `POST` | `/reports` | report-ready JSON → PDF 보고서 생성·반환 |

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d @src/sample_data.json \
  -o daily_report.pdf
```

## 한 줄 요약

한국어 온라인 이슈 데이터를 정제해, 사람이 바로 활용할 수 있는 일일 여론 보고서 PDF로 자동 변환하는 프로젝트입니다.
