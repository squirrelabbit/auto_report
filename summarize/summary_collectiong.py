import pandas as pd 

import os
import re
import time
import random
import hashlib
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

def rank_by_popularity(
    df: pd.DataFrame,
    views_col: str = '조회수',
    likes_col: str = '좋아요수',
    comments_col: str = '댓글 수',
    weights: dict = {'조회수':0.5,'좋아요수':0.3,'댓글 수':0.2},
    out_score_col: str = '인기점수',
    out_rank_col: str = '인기순위'
) -> pd.DataFrame:
    """
    세 지표를 퍼센타일(0~1)로 정규화 후 가중 평균으로 인기점수 산출 → 내림차순 정렬.
    - 높은 값일수록 더 큰 퍼센타일을 갖도록 rank(pct=True) 사용
    - 가중치는 합이 1이 되도록 자동 정규화
    """
    if weights is None:
        weights = {views_col: 0.5, likes_col: 0.3, comments_col: 0.2}
    # 필요한 컬럼 체크
    for c in [views_col, likes_col, comments_col]:
        if c not in df.columns:
            raise KeyError(f"Column '{c}' not in DataFrame")

    work = df.copy()

    # 숫자화 & NaN -> 0
    for c in [views_col, likes_col, comments_col]:
        work[c] = pd.to_numeric(work[c], errors='coerce').fillna(0)

    # 퍼센타일(큰 값일수록 큰 점수): rank(pct=True)는 기본 ascending=True라
    # 작은 값 0에 가깝고 큰 값 1.0에 가까운 값을 줌
    v_pct = work[views_col].rank(pct=True)
    l_pct = work[likes_col].rank(pct=True)
    c_pct = work[comments_col].rank(pct=True)

    # 가중치 정규화
    wsum = sum(weights.get(k, 0.0) for k in [views_col, likes_col, comments_col]) or 1.0
    wv = weights.get(views_col, 0.0) / wsum
    wl = weights.get(likes_col, 0.0) / wsum
    wc = weights.get(comments_col, 0.0) / wsum

    # 인기점수 (0~1)
    score = wv * v_pct + wl * l_pct + wc * c_pct
    work[out_score_col] = (score * 100).round(3)  # 보기 좋게 0~100으로도 표시

    # 인기순위(1이 최상위). 동점이면 같은 순위(dense) → 그다음 정렬은 부가 기준 사용 가능
    work[out_rank_col] = work[out_score_col].rank(ascending=False, method='dense').astype(int)

    # 정렬: 인기점수 내림차순 → (동점일 때) 조회수/좋아요/댓글로 추가 정렬
    work = work.sort_values(
        by=[out_score_col, views_col, likes_col, comments_col],
        ascending=[False, False, False, False]
    ).reset_index(drop=True)

    return work

def source_data_filtering(sorce_path,keyword='APEC 정상회의'):
    df = pd.read_excel(sorce_path,engine='openpyxl')
    df = df[df['수집키워드'] == keyword] 
    sub = df.loc[:, ['URL','조회수','좋아요수','댓글 수']].copy()
    sub['URL'] = sub['URL'].astype(str).str.strip()
    sub = sub.dropna(subset=['URL'])
    distinct_df = sub.drop_duplicates(subset=['URL'], keep='first')
    return rank_by_popularity(distinct_df)
    
    
def slugify_from_url(url: str, max_len: int = 80) -> str:
    """
    URL로 안전한 파일명을 만든다. 충돌 방지를 위해 짧은 해시를 덧붙인다.
    """
    u = urlparse(url)
    path = unquote(u.path).rstrip("/")
    base = path.split("/")[-1] if path and path != "/" else u.netloc
    base = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", base or "index")
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{base[:max_len]}_{h}.txt" 

def html_to_text(html: str) -> str:
    """
    HTML → 본문 텍스트 추출 (스크립트/스타일/네비게이션 제거, 공백 정리)
    """
    soup = BeautifulSoup(html, "lxml")  # lxml이 없으면 "html.parser"로 바꿔도 됨
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # 줄별 공백 정리 + 빈 줄 제거
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines) 

def fetch(url: str, session: requests.Session, timeout=(10, 20)) -> str:
    """
    단일 URL GET (User-Agent 지정, 인코딩 보정)
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; URLTextFetcher/1.0)"}
    resp = session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    # 인코딩 추정 보정
    resp.encoding = resp.encoding or resp.apparent_encoding
    return resp.text


def fetch_and_save_urls(
    urls,
    out_dir: str = "downloaded_texts",
    combine_file: str | None = None,
    raw_html: bool = False,
    retries: int = 2,
    sleep_range=(0.3, 1.2),
):
    """
    urls: URL 리스트
    out_dir: URL별 개별 .txt 저장 디렉토리
    combine_file: 전체를 하나의 파일로 합쳐 저장하고 싶으면 경로 지정
    raw_html: True면 HTML 원문 저장, False면 본문 텍스트만 저장
    retries: 실패 시 재시도 횟수
    sleep_range: 요청 간 랜덤 대기(저쪽 서버 예의 + 차단 회피)
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    combined_chunks = []
    error_log = out / "errors.log"

    with requests.Session() as s:
        for url in tqdm(urls, desc="Fetching"):
            if not url:
                continue
            fname = slugify_from_url(url)
            target_path = out / fname

            last_err = None
            for attempt in range(retries + 1):
                try:
                    html = fetch(url, s)
                    text = html if raw_html else html_to_text(html)
                    target_path.write_text(text, encoding="utf-8")

                    if combine_file:
                        combined_chunks.append(f"URL: {url}\n{'='*80}\n{text}\n\n")
                    # 예의상 잠깐 쉼
                    time.sleep(random.uniform(*sleep_range))
                    break
                except Exception as e:
                    last_err = e
                    # 지수 백오프
                    time.sleep(0.8 * (attempt + 1))
            else:
                # 모든 재시도 실패 → 로그 남김
                with error_log.open("a", encoding="utf-8") as f:
                    f.write(f"[ERROR] {url} -> {last_err}\n")

    if combine_file and combined_chunks:
        Path(combine_file).parent.mkdir(parents=True, exist_ok=True)
        Path(combine_file).write_text("".join(combined_chunks), encoding="utf-8")
    
    
    
    
if __name__ == "__main__":
    urls = source_data_filtering(".\\datas\\문화체육관광부_수집_데이터_251105.xlsx")
    print(urls)
    '''
    fetch_and_save_urls(
        urls['URL'].tolist(),
        out_dir="articles",                 # URL별 개별 .txt 파일
        combine_file=None,    # 전체 합친 파일(선택)
        raw_html=False,                  # True면 HTML 원문 저장
        retries=2,
        sleep_range=(0.3, 1.2),
    )
    '''