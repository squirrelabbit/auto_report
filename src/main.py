from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import json

def generate_pdf(data, output_path="daily_report.pdf"):
    env = Environment(loader=FileSystemLoader("report_templates"))
    template = env.get_template("daily.html")

    html_out = template.render(**data)
    HTML(string=html_out).write_pdf(output_path, stylesheets=["report_templates/report.css"])

if __name__ == "__main__":
    with open("sample_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    generate_pdf(data)

from report_ready.assemble import build_report_json
from report_ready.validate_fields import validate_report_json
from pdf_generator.render_html import render_html
from pdf_generator.generate_pdf import generate_pdf

# 1) Processed Layer에서 불러왔다는 가정
# processed_rows = [...]  # DB 데이터

# 2) Report-ready JSON 생성
# report_json = build_report_json(processed_rows)
with open("sample_data.json", "r", encoding="utf-8") as f:
    report_json = json.load(f)

# 3) 데이터 유효성 검증
# validate_report_json(report_json)

# 4) Jinja2 템플릿 렌더링
html = render_html("daily.html", report_json)

# 5) PDF 생성
generate_pdf(
    html,
    "daily_report.pdf",
    css_path="report_templates/report.css"
)
