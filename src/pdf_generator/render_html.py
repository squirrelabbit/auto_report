# pdf_generator/render_html.py

from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any
import os


def render_html(template_name: str, data: Dict[str, Any], template_dir: str = "report_templates") -> str:
    """
    Jinja2 템플릿을 로딩해서 HTML 문자열로 렌더링한다.
    """

    if not os.path.exists(template_dir):
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    template = env.get_template(template_name)

    html_output = template.render(**data)

    return html_output
