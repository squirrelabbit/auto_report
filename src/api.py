# api.py
# FastAPI 기반 보고서 자동 생성 API.
# report-ready JSON을 받아 검증 → HTML 렌더링 → PDF 생성까지 하나의 요청으로 처리한다.
#
# 실행:
#   uvicorn api:app --reload  (src/ 디렉터리에서)

import os
import tempfile
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from report_ready.validate_fields import validate_report_json
from pdf_generator.render_html import render_html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "report_templates")
CSS_PATH = os.path.join(TEMPLATE_DIR, "report.css")
DEFAULT_TEMPLATE = "daily.html"

app = FastAPI(
    title="auto_report API",
    description="report-ready JSON을 받아 일일 여론 보고서 PDF를 생성하는 API",
    version="0.1.0",
)


@app.get("/health")
def health() -> Dict[str, str]:
    """서비스 상태 확인용."""
    return {"status": "ok"}


@app.post("/reports/validate")
def validate_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    report-ready JSON의 구조만 검증한다.
    PDF를 만들기 전에 데이터 준비 단계에서 호출해 실패를 조기에 잡는 용도.
    """
    try:
        validate_report_json(data)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"valid": True, "sections": len(data["sections"])}


@app.post(
    "/reports",
    responses={200: {"content": {"application/pdf": {}}}},
)
def create_report(data: Dict[str, Any]) -> Response:
    """
    report-ready JSON을 받아 PDF 보고서를 생성해 반환한다.

    처리 순서는 배치(main.py)와 동일하다:
    검증 → Jinja2 템플릿 렌더링 → WeasyPrint PDF 생성.
    """
    try:
        validate_report_json(data)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    html = render_html(DEFAULT_TEMPLATE, data, template_dir=TEMPLATE_DIR)

    # WeasyPrint(네이티브 의존성)는 PDF 생성 시점에만 로딩한다.
    from pdf_generator.generate_pdf import generate_pdf

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        output_path = tmp.name

    try:
        generate_pdf(html, output_path, css_path=CSS_PATH, base_url=TEMPLATE_DIR)
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

    filename = f"{data.get('report_date', 'report')}_daily_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
