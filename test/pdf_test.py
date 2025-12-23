# -*- coding: utf-8 -*-
# WeasyPrint를 사용하여 HTML을 PDF로 변환하고 글꼴을 내장(Embed)하는 Python 스크립트입니다.
# 실행 전: pip install weasyprint
from weasyprint import HTML, CSS
import os

# --- 1. 최종 보고서 HTML 내용 정의 ---

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM 기반 일일 정책 여론 종합 보고서 (최종 완성본)</title>
    
    <style>
        /* 폰트 내장을 위한 CSS: Nanum Gothic을 명확히 선언 */
        @font-face {
            font-family: 'NanumGothic';
            src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_two@1.0/NanumGothic.woff') format('woff');
            font-weight: normal;
            font-style: normal;
        }

        /* ---------------------------------- */
        /* Native CSS (WeasyPrint 최적화 및 페이지 분할 제어) */
        /* ---------------------------------- */
        body {
            font-family: 'NanumGothic', sans-serif;
            font-size: 9pt; 
            margin: 0;
            padding: 0;
            line-height: 1.5;
        }
        .report-slide {
            width: 780px; /* 폭 약간 증가하여 가로 텍스트 잘림 방지 */
            padding: 30px;
            margin: 0 auto;
        }
        /* 페이지 분할 제어: 섹션 시작 시 강제 개행 */
        section {
            page-break-inside: avoid;
            page-break-after: avoid; 
        }
        /* 두 번째 섹션부터는 새 페이지 시작 */
        .page-break-start {
             page-break-before: always;
        }
        
        .header { border-bottom: 4px solid #1034a6; padding-bottom: 10px; margin-bottom: 20px; }
        .flex { display: flex; }
        .justify-between { justify-content: space-between; }
        .align-center { align-items: center; }
        .font-extrabold { font-weight: 800; }
        .text-3xl { font-size: 20pt; }
        .text-base { font-size: 10pt; }
        .text-xs { font-size: 8pt; }
        .text-sm { font-size: 9pt; }
        .text-xl { font-size: 14pt; }
        .text-wise-blue { color: #1034a6; }
        .text-wise-green { color: #10b981; }
        .border-l-4 { border-left: 4px solid; padding-left: 8px; }
        
        /* 박스 및 그리드 스타일 */
        .box-container { border: 1px solid #ddd; border-radius: 6px; padding: 10px; background-color: white; }
        .top-issue-grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .top-issue-grid th, .top-issue-grid td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        .top-issue-grid th { background-color: #f0f4f8; font-weight: bold; }
        
        /* 일반 테이블 스타일 */
        .report-table { width: 100%; border-collapse: collapse; }
        .report-table th, .report-table td { border: 1px solid #ddd; padding: 6px; text-align: left; }
        .report-table th { background-color: #f9fafb; font-weight: bold; }
        .llm-summary { border-left: 4px solid #1034a6; padding-left: 8px; margin-top: 5px; font-style: italic; }
        
        /* 시각화 CSS */
        .sentiment-visual-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .sentiment-visual-table th, .sentiment-visual-table td { border: none; padding: 4px; font-size: 8pt; text-align: left; }
        .sentiment-bar-row { height: 12px; display: flex; width: 100%; }
        .segment { height: 100%; display: inline-block; }
        .positive-segment { background-color: #22c55e; }
        .negative-segment { background-color: #ef4444; }
        .neutral-segment { background-color: #9ca3af; }
        
        /* 목록 스타일 */
        .list-style-none { list-style: none; padding-left: 0; margin-top: 0; }
        .list-style-none li { margin-bottom: 4px; display: flex; }
        .list-style-none .icon { margin-right: 5px; flex-shrink: 0; font-size: 12pt; line-height: 1; }
        .icon-check { color: #10b981; }
        .icon-arrow { color: #ef4444; }

    </style>
</head>
<body>

    <div class="report-slide">
        
        <!-- 1. 보고서 헤더 및 제목 -->
        <header class="header">
            <div class="flex justify-between align-center">
                <h1 class="text-3xl font-extrabold text-wise-blue">온라인 일일 여론 종합</h1>
                <p class="text-base font-semibold">문화체육관광부 | 2025. 11. 17. (월) (자동 생성)</p>
            </div>
        </header>

        <!-- 핵심 1단 레이아웃 (LLM 통합) -->
        <div style="margin-top: 20px;">
            
            <!-- ====== TOP 이슈 요약 및 매체별 이슈 (섹션 1) ====== -->
            <section>
                <h2 class="text-xl font-bold text-gray-800 mb-4 border-l-4 border-wise-green pl-2">오늘의 TOP3 정책 이슈</h2>
                
                <!-- TOP 이슈 요약 (안정적인 테이블로 대체) -->
                <table class="top-issue-grid mb-6">
                    <thead>
                        <tr>
                            <th style="width: 33%;">정책 이슈 1 (환율)</th>
                            <th style="width: 33%;">정책 이슈 2</th>
                            <th style="width: 33%;">정책 이슈 3</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <p class="text-xl font-bold text-gray-800">환율 등 글로벌 경제</p>
                                <p class="text-sm text-gray-600">언급량 1,284건 (<span style="color: #ef4444;">▲616</span>)</p>
                            </td>
                            <td>
                                <p class="text-xl font-bold text-gray-800">새벽배송 제한 논란</p>
                                <p class="text-sm text-gray-600">언급량 271건 (▲4)</p>
                            </td>
                            <td>
                                <p class="text-xl font-bold text-gray-800">전동킥보드 단속</p>
                                <p class="text-sm text-gray-600">언급량 160건 (<span style="color: #ef4444;">▼69</span>)</p>
                            </td>
                        </tr>
                    </tbody>
                </table>

                <!-- 매체별 TOP 이슈 (하이퍼링크 및 관심도) -->
                <h2 class="text-xl font-bold text-gray-800 mb-3 border-l-4 border-wise-green pl-2">매체별 TOP 이슈 (하이퍼링크 및 관심도)</h2>
                <div class="box-container text-sm" style="background-color: #f9fafb;">
                    <p class="font-bold text-wise-blue mb-2">NEWS (최다댓글)</p>
                    <p class="mb-3">○ [조선일보] 李대통령 "통신보안 잘 됩니까?" 시진핑 "뒷문 있나 보세요" (댓글 704건)</p>
                    <p class="font-bold text-wise-blue mb-2">COMMUNITY (최다조회)</p>
                    <p class="mb-3">○ [인스티즈] 어제 apec정상회담 레전드 장면 ㅋㅋ (조회수 91,050회)</p>
                    <p class="font-bold text-wise-blue mb-2">YOUTUBE (최다조회)</p>
                    <p>○ [JTBC News] 시진핑 주석 마음이 '스르륵' 열린 순간...모두 '빵' 터졌다 (조회수 1,257,492회)</p>
                </div>
            </section>
            
            <!-- ====== 주요 이슈 소개 및 내용 요약 (LLM 통합 본문 - 섹션 2) ====== -->
            <!-- 이 섹션부터 다음 페이지로 넘어가도록 강제합니다. (PDF 깔끔한 분할) -->
            <section class="page-break-start">
                <h2 class="text-xl font-bold text-gray-800 mb-3 border-l-4 border-wise-green pl-2">환율 등 글로벌 경제 (주요 이슈 소개 및 내용 요약)</h2>
                
                <!-- 1. LLM 자동 순화된 핵심 여론 요약 (어조 일관성 확보) -->
                <div class="llm-summary-box mb-4">
                    <div class="mb-2 pb-2" style="border-bottom: 1px solid #ddd;">
                         <p class="font-bold text-wise-blue text-base">✅ LLM 자동 순화된 핵심 여론 요약 (중요도 상위 작성)</p>
                    </div>
                    
                    <!-- LLM 순화 결과 표시 영역 (Hardcoded Final Result) -->
                    <p id="llm-refined-summary" class="text-sm text-gray-700 leading-relaxed llm-summary">
                        글로벌 금리 인상 가속화 우려로 인한 환율 급등세가 관찰되고 있으며, 이에 대한 국민적 불안감이 온라인 여론에서 강하게 표출되고 있습니다. 정부는 단기적 시장 개입 정책을 수행 중이나, 근본적인 물가 및 금융 안정화 대책에 대한 명확한 커뮤니케이션이 요구됩니다.
                    </p>
                    
                    <!-- Reviewer Agent 품질 검증 (Hardcoded Final Result) -->
                    <div class="flex justify-between align-center mt-3 pt-3" style="border-top: 1px solid #ddd;">
                        <span class="text-xs font-semibold text-gray-600">Reviewer Agent 품질 검증 및 신뢰도 점수</span>
                        <span id="reviewer-score" class="text-xl font-extrabold text-wise-green">99/100</span>
                    </div>
                </div>

                <!-- 원본 여론 (LLM 입력 텍스트) 및 기사/댓글 -->
                <div class="flex mb-6">
                    <!-- 주요 기사 영역 -->
                    <div class="box-container" style="width: 50%; margin-right: 15px;">
                        <p class="text-sm font-semibold mb-2 border-b" style="padding-bottom: 5px;">⚫️ 주요 기사 목록</p>
                        <ul id="article-list" class="list-style-none text-sm space-y-1">
                            <li><span class="icon icon-check">✓</span> [서울] 1400원 턱밑 환율에도 표한 수 없는 정부</li>
                            <li><span class="icon icon-check">✓</span> [MBC] 미국발 '울트라 스텝' 우려에 한국도 출렁 - 한은 금리 얼마나 올릴까?</li>
                        </ul>
                    </div>
                    <!-- 댓글 여론 영역 -->
                    <div class="box-container" style="width: 50%;">
                        <p class="text-sm font-semibold mb-2 border-b" style="padding-bottom: 5px;">⚫️ 여론을 대표하는 댓글</p>
                        <ul id="raw-sentiment-list" class="list-style-none text-sm space-y-1">
                            <li><span class="icon icon-arrow">▶</span> "고금리와 고환율의 콜라보, 현재 상태로는 답이 없다"</li>
                            <li><span class="icon icon-arrow">▶</span> "금리 1%p 올려도 부족하다. 금융위기 오기 전에 선제적으로 대응해라"</li>
                            <li><span class="icon icon-arrow">▶</span> "미국이 올트라 스텝 운운하는데 한은 너무 소극적이다. 국민들 다 죽기 전 물가부터 잡아"</li>
                        </ul>
                    </div>
                </div>
            </section>

            <!-- 2. 연관어 및 감성연관어 비교 시각화 (섹션 3) -->
            <section style="margin-top: 30px;">
                <h2 class="text-xl font-bold text-gray-800 mb-3 border-l-4 border-wise-green pl-2">데이터 분석 상세 (연관어 및 감성 비교)</h2>

                <div class="flex mb-4">
                    <!-- 연관 키워드 표 (명시성 강화) -->
                    <div class="box-container" style="width: 50%; margin-right: 15px;">
                        <p class="text-sm font-semibold mb-2 border-b" style="padding-bottom: 5px;">주요 연관어 언급량 비교</p>
                        <table class="report-table">
                            <thead>
                                <tr style="background-color: #eee;">
                                    <th style="width: 15%;">순위</th>
                                    <th style="width: 50%;">정책 연관어</th>
                                    <th>언급량</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td>1</td><td class="font-medium">환율</td><td>867건</td></tr>
                                <tr><td>2</td><td class="font-medium">물가</td><td>854건</td></tr>
                                <tr><td>3</td><td class="font-medium">금리</td><td>647건</td></tr>
                                <tr><td>4</td><td class="font-medium">코스피</td><td>568건</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <!-- 감성 연관어 시각화 (테이블 구조 기반) -->
                    <div class="box-container" style="width: 50%;">
                        <p class="text-sm font-semibold mb-2 border-b" style="padding-bottom: 5px;">뉴스 vs 소셜미디어 감성 연관어 시각화</p>
                        <table class="sentiment-visual-table">
                            <thead>
                                <tr style="border-bottom: 1px solid #ddd;">
                                    <th style="width: 15%;">매체</th>
                                    <th style="width: 85%;">감성 비율 (긍정/부정/중립)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>뉴스</td>
                                    <td>
                                        <div class="sentiment-bar-row">
                                            <div class="segment positive-segment" style="width: 40%;"></div>
                                            <div class="segment negative-segment" style="width: 21%;"></div>
                                            <div class="segment neutral-segment" style="width: 39%;"></div>
                                        </div>
                                        <p class="text-xs" style="margin-top: 2px;">긍정 40%, 부정 21%, 중립 39%</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td>소셜</td>
                                    <td>
                                        <div class="sentiment-bar-row">
                                            <div class="segment positive-segment" style="width: 39%; background-color: #6366f1;"></div>
                                            <div class="segment negative-segment" style="width: 39%; background-color: #f97316;"></div>
                                            <div class="neutral-segment" style="width: 22%; background-color: #9ca3af;"></div>
                                        </div>
                                        <p class="text-xs" style="margin-top: 2px;">긍정 39%, 부정 39%, 중립 22%</p>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <p class="text-xs text-red-600 mt-2 text-center font-medium">소셜미디어의 부정 감성(39%)이 뉴스(21%) 대비 극심한 양상을 보임.</p>
                    </div>
                </div>

                <!-- 3. 정책 대응 가이드라인 (섹션 4) -->
                <div style="padding: 15px; background-color: #e8f5e9; border: 1px solid #10b981; border-radius: 8px;">
                    <div style="padding-bottom: 8px; border-bottom: 1px solid #ccc;">
                        <h3 class="text-base font-extrabold text-gray-800 flex items-center">
                            정책 대응 가이드라인
                        </h3>
                    </div>
                    
                    <ul class="list-style-none space-y-2" style="padding-top: 10px;">
                        <li><span class="icon icon-check">✓</span> <b>커뮤니케이션 전략:</b> '단순한 시장 안정 노력'보다 '국민 가계 안정화'에 초점을 맞춘 공감 기반 서술을 최우선으로 해야 합니다.</li>
                        <li><span class="icon icon-check">✓</span> <b>민감어 관리:</b> '고금리', '고환율 쇼크' 등의 민감어 사용을 최소화하고, 이를 대체할 '점진적 안정화', '리스크 관리 강화' 등의 용어를 사용합니다.</li>
                        <li><span class="icon icon-check">✓</span> <b>즉각적 대응 권고:</b> 정부의 정책 의도와 향후 계획을 담은 구체적인 Q&A 문답 자료를 배포하여 국민적 불안을 해소해야 합니다. (기관: 기획재정부, 금융위원회)</li>
                    </ul>
                </div>
            </section>
        </div>

        <!-- 보고서 푸터 -->
        <footer style="margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; text-align: center; font-size: 8pt; color: #aaa;">
            문화체육관광부 | WISE NUT (LLM 자동 보고 체계)
        </footer>
    </div>
</body>
</html>
"""
# 폰트 처리를 위해 HTML_CONTENT 내부 <style> 태그에 Nanum Gothic을 명시적으로 선언했습니다.

# --- 2. PDF 변환 함수 정의 ---
def create_pdf_report(html_content, output_filename="automated_report_final_v2.pdf"):
    """
    HTML 콘텐츠를 WeasyPrint를 사용하여 PDF로 변환하고 파일을 저장합니다.
    """
    try:
        # HTML 객체 생성
        html = HTML(string=html_content, base_url=os.path.dirname(os.path.abspath(__file__)) if __file__ else '.') 

        # PDF 생성
        html.write_pdf(output_filename)

        print(f"PDF 보고서가 성공적으로 생성되었습니다: {output_filename}")
        print("WeasyPrint는 HTML 내부의 @font-face 선언을 사용하여 글꼴을 PDF에 내장합니다.")
        return True
    
    except ImportError:
        print("오류: WeasyPrint가 설치되지 않았습니다. 'pip install weasyprint'를 실행해 주세요.")
        return False
    except Exception as e:
        print(f"PDF 생성 중 오류가 발생했습니다: {e}")
        return False

# --- 3. 스크립트 실행 ---
if __name__ == "__main__":
    # PDF 생성
    create_pdf_report(HTML_CONTENT)