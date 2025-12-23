# report_ready/validate_fields.py

from typing import Dict, Any


REQUIRED_FIELDS = [
    "report_title",
    "report_date",
    "report_unit",
    "sections"
]


def validate_report_json(data: Dict[str, Any]):
    """
    템플릿 변환 전에 데이터 구조가 올바른지 검증한다.
    필수 항목이 없으면 에러 발생.
    """

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(data["sections"], list):
        raise TypeError("`sections` must be a list")

    for sec in data["sections"]:
        if "section_name" not in sec:
            raise ValueError("Each section must contain 'section_name'")

        if "issues" not in sec:
            raise ValueError("Each section must contain 'issues'")

        if not isinstance(sec["issues"], list):
            raise TypeError("'issues' must be a list")

    return True
