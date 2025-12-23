from typing import Iterable, List, Optional, Tuple
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
from summary_preprocessing import Deduper, KoreanTokenizer, build_stopwords, save_jsonl

def source_data_filtering(sorce_path,keyword='APEC 정상회의'):
    df = pd.read_excel(sorce_path,engine='openpyxl')
    coments = df[df['수집키워드'] == keyword]
    urls = set(coments['URL'].tolist())
    
    coment_cluster = {}
    for url in urls: 
        sub_coments = coments[coments['URL'] == url]
        contents = sub_coments['댓글 내용'].dropna().tolist()
        if len(contents) >= 10:
            coment_cluster[slugify_from_url(url)] = sub_coments['댓글 내용'].tolist() 
    return coment_cluster
    
    
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


def run_pipeline(
    docs: Iterable[Tuple[str,str,int]],
    stopwords_path: Optional[str],
    decision: str = "union",
    simhash_k: int = 3,
    minhash_threshold: float = 0.80,
    token_min_len: int = 2
) -> Tuple[List[dict], List[dict]]:
    """
    returns:
      kept_records: [{id, text, tokens}]
      dup_records : [{id, text, reason, duplicate_of(list)}]
    """
    stopwords = build_stopwords(stopwords_path)
    tokenizer = KoreanTokenizer(stopwords=stopwords, min_len=token_min_len)

    deduper = Deduper(
        simhash_bits=64,           # 64 → 128로 확장
        simhash_k=simhash_k,                # 허용 해밍 거리(기존 3보다 약간 완화)
        minhash_perm=128,           # MinHash 샘플 수도 128 → 256으로 증가
        minhash_threshold=minhash_threshold,     # 기사 유사도 85% 이상을 중복으로 간주
        decision=decision            # SimHash나 MinHash 둘 중 하나라도 중복이면 제거
    )

    kept = []
    dups = []

    for id, txt in enumerate(tqdm(docs, desc="Preprocessing")):
        doc_id = f"comment_id_{id} "
        tokens = tokenizer.tokenize(txt)
        if not tokens:
            # 빈문서 취급 → 버리되 reason 기록
            dups.append({
                "id": doc_id,
                "text": txt,
                "reason": {"empty_or_stopword_only": True},
                "duplicate_of": []
            })
            continue

        is_dup, reasons = deduper.check_duplicate(doc_id, tokens)
        if is_dup:
            # 중복: 사유/대상 기록
            duplicate_of = list(set(reasons["simhash"] + reasons["minhash"]))
            dups.append({
                "id": doc_id,
                "text": txt,
                "reason": reasons,
                "duplicate_of": duplicate_of
            })
        else:
            deduper.add(doc_id, tokens)
            kept.append({
                "id": doc_id,
                "text": txt,
                "tokens": tokens,
            })

    return kept, dups
    
    
if __name__ == "__main__":
    '''
    comment_cluster = source_data_filtering(".\\datas\\문화체육관광부_수집_데이터_251105.xlsx")
    
    args = {
        "origin_dir": ".\\datas\\문화체육관광부_수집_데이터_251105.xlsx",
        "sorce_dir" : '.\\articles',
        "stopwords" : None,
        "decision" : "union", #["union", "intersection"],
        "simhash_k" : 5,
        "minhash_threshold" : 0.60,
        "min_token_len" : 2,
        "output" : '.\\check_comments_dup\\', 
        "dups" : '.\\check_comments_dup\\',
    }
    
    for filename, comments in comment_cluster.items():
        kept, dups = run_pipeline(
            docs=comments,
            stopwords_path=args['stopwords'],
            decision=args['decision'],
            simhash_k=args['simhash_k'],
            minhash_threshold=args['minhash_threshold'],
            token_min_len=args['min_token_len']
        )

        # 저장
        save_jsonl(kept, f"{args['output']}{filename}_unique.json")
        if args['dups']:
            save_jsonl(dups, f"{args['dups']}{filename}_dups.json")

        print(f"[OK] kept={len(kept)}  dups={len(dups)}")
        print(f" - saved cleaned to: {args['output']}")
        if args['dups']:
            print(f" - saved duplicates to: {args['dups']}")
    ''' 
    
    import json,os 
    
    root = ".\\check_comments_dup"
    article_root = ".\\articles"
    paths = [f"{root}\\{filename}" for filename in os.listdir(root) if 'unique' in filename]
    jsons = [(os.path.basename(path).replace("_unique.json","") , json.load(open(path,'r',encoding="utf-8"))) for path in paths if 'unique' in path]
    jsons = sorted(jsons, key=lambda x: len(x[1]), reverse=True)[:3]
    finals = [(name,open(f"{article_root}\\{name}","r",encoding='utf-8').read(),[comment['text'] for comment in comments]) for name,comments in jsons]
    
    for name, article, comments in finals:
        
        with open(f".\\comments_summary_{name}",'w',encoding="utf-8") as f:
            prompt = f'''다음은 한국어 기사에 대한 본문 내용과 그 기사에 달린 독자 댓글들이다. 기사 본문과 댓글들의 핵심 내용을 바탕으로, 기사에 대한 독자들의 전반적인 반응과 의견을 요약해줘. 요약문은 5문장 이내로 작성해줘.
                        기사 본문:\n
                        {article}\n\n
                        --------------------------------\n
                        독자 댓글들:\n
                        {"\n".join(comments)}\n
                        '''
            f.write(prompt)