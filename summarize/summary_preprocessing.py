# -*- coding: utf-8 -*-
"""
Korean preprocessing pipeline:
- Stopword removal
- Lemmatization (어근/기본형 추출)
- Near-duplicate removal with BOTH SimHash and MinHash

Tech stack: KoNLPy (Okt), Kiwi, simhash, datasketch
Usage:
    python preprocess_kor.py --input input.txt --output cleaned.jsonl
    # or feed a CSV/TSV with a column name
    python preprocess_kor.py --input data.csv --col text --output cleaned.jsonl
"""

import argparse
import csv
import json
import os
import re
from typing import Iterable, List, Tuple, Dict, Optional, Set

from tqdm import tqdm
import regex as re2

# --- NLP tools ---
from konlpy.tag import Okt                # KoNLPy
from kiwipiepy import Kiwi                # Kiwi

# --- Dedup tools ---
from simhash import Simhash, SimhashIndex
from datasketch import MinHash, MinHashLSH

from summary_collectiong import source_data_filtering,slugify_from_url


############################################################
# Text normalization / tokenization
############################################################

URL_RE   = re2.compile(r"""https?://[^\s]+|www\.[^\s]+""", re2.I)
MAIL_RE  = re2.compile(r"""[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}""")
HTML_RE  = re2.compile(r"<[^>]+>")
NUM_RE   = re2.compile(r"\d+([,.]\d+)*")
SPACE_RE = re2.compile(r"\s+")

# 남길 품사(한국어 기준) — 필요에 맞게 조정
KIWI_KEEP_TAGS = {
    "NNG", "NNP",  # 일반/고유 명사
    "VV", "VA", "VX",  # 동사/형용사/보조용언
    "MM", "MAG", "XR"  # 관형사/일반부사/어근
}
OKT_KEEP_TAGS = {
    "Noun", "Verb", "Adjective", "Adverb", "Modifier"
}


def basic_normalize(text: str) -> str:
    """URL/메일/HTML/숫자 제거 + 공백 정리."""
    text = URL_RE.sub(" ", text)
    text = MAIL_RE.sub(" ", text)
    text = HTML_RE.sub(" ", text)
    text = NUM_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text


class KoreanTokenizer:
    """
    - Kiwi 로 1차 토큰화(POS 기준 필터)
    - 동사/형용사 계열은 Okt(stem=True)로 기본형 보정
    => '어근 추출' 실용적 구현
    """
    def __init__(self,
                 stopwords: Optional[Set[str]] = None,
                 kiwi_keep_tags: Optional[Set[str]] = None,
                 okt_keep_tags: Optional[Set[str]] = None,
                 min_len: int = 2):
        self.kiwi = Kiwi()
        self.okt = Okt()
        self.stopwords = stopwords or set()
        self.kiwi_keep = kiwi_keep_tags or KIWI_KEEP_TAGS
        self.okt_keep = okt_keep_tags or OKT_KEEP_TAGS
        self.min_len = min_len

    def _okt_stem_words(self, words: List[str]) -> List[str]:
        """Okt를 사용해 동사/형용사에 대해 기본형(stem)으로 보정."""
        stems: List[str] = []
        for w in words:
            for tok, tag in self.okt.pos(w, stem=True):
                if tag in self.okt_keep and len(tok) >= self.min_len:
                    stems.append(tok)
        return stems

    def tokenize(self, text: str) -> List[str]:
        text = basic_normalize(text)

        # 1) Kiwi 토큰화
        toks = self.kiwi.tokenize(text, normalize_coda=True)
        # 품사 필터 + 최소 길이
        kiwi_kept = [(t.form, t.tag) for t in toks
                     if (t.tag in self.kiwi_keep) and (len(t.form) >= self.min_len)]

        # 2) 동사/형용사 계열은 Okt로 기본형 보정
        vv_va_vx = [w for (w, tag) in kiwi_kept if tag in {"VV", "VA", "VX"}]
        base_forms = self._okt_stem_words(vv_va_vx) if vv_va_vx else []

        # 3) 나머지(명사/어근/관형사/부사 등)는 표면형 사용
        others = [w for (w, tag) in kiwi_kept if tag not in {"VV", "VA", "VX"}]

        # 통합 + 불용어 제거
        tokens = []
        for w in base_forms + others:
            if (w not in self.stopwords) and (len(w) >= self.min_len):
                tokens.append(w)
        return tokens


############################################################
# MinHash/SimHash utilities
############################################################

def make_shingles(tokens: List[str], n: int = 3) -> Set[str]:
    """단어 n-gram 셋(중복 제거). 한국어는 형태소 단위 n-gram이 안정적."""
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def build_minhash(shingles: Iterable[str], num_perm: int = 128) -> MinHash:
    mh = MinHash(num_perm=num_perm)
    for sh in shingles:
        mh.update(sh.encode("utf-8"))
    return mh


def build_simhash(tokens: Iterable[str], fbits: int = 64) -> Simhash:
    # simhash는 feature 빈도/가중치 반영 가능: (feature, weight) 형태도 허용
    return Simhash(list(tokens), f=fbits)


############################################################
# Deduper that applies BOTH SimHash and MinHash
############################################################

class Deduper:
    """
    - SimHashIndex 로 빠른 near-dup 탐지 (해밍 거리 k 이내)
    - MinHashLSH 로 Jaccard 유사도 기반 후보 탐지
    - '둘 중 하나라도' 유사하면 중복으로 간주(기본)
    """
    def __init__(self,
                 simhash_bits: int = 64,
                 simhash_k: int = 3,                 # 허용 해밍거리 (작을수록 엄격)
                 minhash_perm: int = 128,
                 minhash_threshold: float = 0.80,    # Jaccard 유사도 임계값
                 minhash_lsh_bands: Optional[int] = None,
                 decision: str = "union"             # 'union' or 'intersection'
                 ):
        assert decision in {"union", "intersection"}
        self.fbits = simhash_bits
        self.k = simhash_k
        self.decision = decision

        # SimHash 인덱스
        self._sim_items: Dict[str, Simhash] = {}
        self._sim_index = SimhashIndex(self._sim_items.items(), k=self.k,f=self.fbits)

        # MinHash LSH
        self.num_perm = minhash_perm
        if minhash_lsh_bands is None:
            # datasketch는 threshold로 내부 파라미터 자동 설정 가능
            self._lsh = MinHashLSH(threshold=minhash_threshold, num_perm=self.num_perm)
        else:
            self._lsh = MinHashLSH(num_perm=self.num_perm, params=(minhash_lsh_bands, self.num_perm // minhash_lsh_bands))
        self._mh_table: Dict[str, MinHash] = {}

    def check_duplicate(self, key: str, tokens: List[str]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        key: 문서 고유키(문자열)
        tokens: 전처리된 토큰
        return: (is_duplicate, {"simhash": [...], "minhash": [...]})
        """
        reasons = {"simhash": [], "minhash": []}

        # --- SimHash 후보 ---
        sh = build_simhash(tokens, fbits=self.fbits)
        sim_dups = self._sim_index.get_near_dups(sh)
        sim_dups = [d for d in sim_dups if d != key]
        if sim_dups:
            reasons["simhash"] = sim_dups

        # --- MinHash 후보 ---
        shingles = make_shingles(tokens, n=3)
        mh = build_minhash(shingles, num_perm=self.num_perm)
        mh_dups = self._lsh.query(mh)
        mh_dups = [d for d in mh_dups if d != key]
        if mh_dups:
            reasons["minhash"] = mh_dups

        # 의사결정
        is_dup = False
        if self.decision == "union":
            is_dup = bool(reasons["simhash"] or reasons["minhash"])
        else:  # intersection
            is_dup = bool(reasons["simhash"] and reasons["minhash"])

        return is_dup, reasons

    def add(self, key: str, tokens: List[str]):
        """중복이 아니라고 판단된 문서를 인덱스에 추가."""
        sh = build_simhash(tokens, fbits=self.fbits)
        self._sim_index.add(key, sh)

        shingles = make_shingles(tokens, n=3)
        mh = build_minhash(shingles, num_perm=self.num_perm)
        self._lsh.insert(key, mh)
        self._mh_table[key] = mh


############################################################
# IO helpers
############################################################

def load_texts(source_dir: str,origin_dir:str) -> Iterable[Tuple[str,str,int]]:
    import os 
    urls = source_data_filtering(origin_dir)['URL'].tolist()
    populers = source_data_filtering(origin_dir)['인기순위'].tolist()
    file_paths = [f"{source_dir}\\{slugify_from_url(url)}" for url in urls]
    print(f"{len(os.listdir(source_dir))}/{len(set(file_paths))}")
    for path, populer in zip(file_paths,populers):
        with open(path, "r", encoding="utf-8") as f:
            yield (".".join(os.path.basename(path).split(".")[:-1]), f.read(),populer)

def save_jsonl(records: List[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


############################################################
# Pipeline runner
############################################################

def build_stopwords(user_path: Optional[str] = None) -> Set[str]:
    """기본 불용어 + 사용자 파일(.txt, 줄바꿈 구분)."""
    base = {
        "것", "수", "등", "및", "고", "과", "의", "이", "가", "은", "는",
        "를", "을", "도", "만", "로", "으로", "에", "에서", "하다", "되다",
        "그러나", "그리고", "하지만", "저", "그", "이러한", "또한", "등등"
    }
    if user_path and os.path.isfile(user_path):
        with open(user_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    base.add(w)
    return base


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
        simhash_bits=128,           # 64 → 128로 확장
        simhash_k=simhash_k,                # 허용 해밍 거리(기존 3보다 약간 완화)
        minhash_perm=256,           # MinHash 샘플 수도 128 → 256으로 증가
        minhash_threshold=minhash_threshold,     # 기사 유사도 85% 이상을 중복으로 간주
        decision=decision            # SimHash나 MinHash 둘 중 하나라도 중복이면 제거
    )

    kept = []
    dups = []

    for doc_id, txt, popluer in tqdm(docs, desc="Preprocessing"):
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
                "populer": popluer
            })

    return kept, dups


############################################################
# CLI
############################################################

def main():
    args = {
        "origin_dir": ".\\datas\\문화체육관광부_수집_데이터_251105.xlsx",
        "sorce_dir" : '.\\articles',
        "stopwords" : None,
        "decision" : "union", #["union", "intersection"],
        "simhash_k" : 5,
        "minhash_threshold" : 0.60,
        "min_token_len" : 2,
        "output" : '.\\check_dup\\uniques.json', 
        "dups" : '.\\check_dup\\duplicates.json',
    }

    kept, dups = run_pipeline(
        docs=load_texts(args['sorce_dir'],args['origin_dir']),
        stopwords_path=args['stopwords'],
        decision=args['decision'],
        simhash_k=args['simhash_k'],
        minhash_threshold=args['minhash_threshold'],
        token_min_len=args['min_token_len']
    )

    # 저장
    save_jsonl(kept, args['output'])
    if args['dups']:
        save_jsonl(dups, args['dups'])

    print(f"[OK] kept={len(kept)}  dups={len(dups)}")
    print(f" - saved cleaned to: {args['output']}")
    if args['dups']:
        print(f" - saved duplicates to: {args['dups']}")


if __name__ == "__main__":
    #main()
    
    import json
    with open(".\\check_dup\\uniques.json",'r',encoding="utf-8") as f:
        unique = json.load(f)
        representations = sorted(list(unique), key=lambda x: x['populer'])[:20]
        ids = [rep['id'] for rep in representations] 
        
        articels = []
        
        for id in ids: 
            with open(f".\\articles\\{id}.txt",'r',encoding="utf-8") as f:
                text = f.read()
                articels.append(text)   
        
        with open(".\\summary.txt",'w',encoding="utf-8") as f:
            prompt = f'''다음은 특정 키워드 에 대한 한국어 기사 20개의 본문이다. 각 기사의 핵심 내용을 바탕으로 최대 3문장의 현 키워드에 대한 언론 동향을 알수 있는 요약문을 생성하라\n\n
                        기사들:\n
                        {"\n\n---\n\n".join(articels)}\n\n 
                        '''
            f.write(prompt)
            
    
    
        