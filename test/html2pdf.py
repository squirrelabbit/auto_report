from weasyprint import HTML
import os

# --- HTML 파일을 PDF로 변환하는 함수 ---
def create_pdf_from_file(html_file_path, output_filename="automated_report.pdf"):
    """
    로컬 HTML 파일을 읽어 WeasyPrint를 통해 PDF로 변환합니다.
    """
    try:
        if not os.path.exists(html_file_path):
            print(f"오류: HTML 파일을 찾을 수 없습니다 → {html_file_path}")
            return False

        # HTML 파일을 WeasyPrint에 전달 (string 대신 filename 사용)
        html = HTML(filename=html_file_path, base_url=os.path.dirname(html_file_path))

        # PDF 생성
        html.write_pdf(output_filename)

        print(f"PDF 보고서가 성공적으로 생성되었습니다: {output_filename}")
        return True

    except ImportError:
        print("오류: WeasyPrint가 설치되지 않았습니다. 'pip install weasyprint' 실행 필요.")
        return False

    except Exception as e:
        print(f"PDF 생성 중 오류가 발생했습니다: {e}")
        return False


# --- 스크립트 실행 ---
if __name__ == "__main__":
    html_path = "sample_report.html"   # 변환할 HTML 파일 경로
    create_pdf_from_file(html_path, "automated_report.pdf")
