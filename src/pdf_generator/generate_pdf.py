# pdf_generator/generate_pdf.py

from weasyprint import HTML, CSS
from typing import Optional
import os


def generate_pdf(
    html_string: str,
    output_path: str,
    css_path: Optional[str] = None,
    base_url: str = "."
):
    """
    렌더링된 HTML 문자열을 PDF로 변환한다.
    css_path가 있으면 스타일 적용.
    """

    stylesheets = []

    if css_path:
        if not os.path.exists(css_path):
            raise FileNotFoundError(f"CSS file not found: {css_path}")
        stylesheets.append(CSS(filename=css_path))

    HTML(string=html_string, base_url=base_url).write_pdf(
        output_path,
        stylesheets=stylesheets
    )

    print(f"PDF 생성 완료 → {output_path}")
