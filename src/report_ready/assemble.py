# report_ready/assemble.py

from typing import Dict, Any, List


def build_report_json(processed_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Processed Layer( Postgres )에서 읽어온 레코드들을
    Daily/Weekly 템플릿에서 바로 사용할 수 있는 JSON 구조로 변환한다.

    processed_rows 예시 구조:
    [
        {
            "date": "2025-11-03",
            "section_name": "대통령실",
            "issue": "한중 정상회담",
            "issue_summary": "...",
            "top_posts": [...],
            "reactions": [...],
            "category": "...",
            "source": "NEWS / COMM / YT",
            ...
        },
        ...
    ]
    """

    if not processed_rows:
        raise ValueError("processed_rows is empty")

    # 보고 날짜는 첫 행 기준
    report_date = processed_rows[0]["date"]

    sections = {}

    # 섹션별 그룹화
    for row in processed_rows:
        sec_name = row["section_name"]

        if sec_name not in sections:
            sections[sec_name] = {
                "section_name": sec_name,
                "issues": []
            }

        issue_block = {
            "issue": row["issue"],
            "issue_summary": row["issue_summary"],
            "top_posts": row.get("top_posts", []),
            "reactions": row.get("reactions", [])
        }

        sections[sec_name]["issues"].append(issue_block)

    return {
        "report_title": "온라인 일일 여론 종합",
        "report_date": report_date,
        "report_unit": "국민소통실",
        "sections": list(sections.values())
    }
