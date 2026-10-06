import re

from rank_bm25 import BM25Okapi
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "and", "or", "for", "on",
    "with", "by", "is", "are", "be", "this", "that", "as", "at",
    "shall", "which", "such", "from", "it", "its",
}

def normalize_e_numbers(text: str) -> str:
    """'E 160 c' 같은 표기를 'E160c'로 통일 (띄어쓰기 제거)"""
    return re.sub(
        r"\bE\s*(\d{3,4})\s*([a-zA-Z]?)\b",
        lambda m: f"E{m.group(1)}{m.group(2)}",
        text,
        flags=re.IGNORECASE,
    )

def tokenize_english(text: str) -> list[str]:
    """영어 텍스트 토큰화: E-번호 정규화 + 소문자화 + 단어 단위 분리 + 불용어 제거"""
    text = normalize_e_numbers(text)
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS]


# ---------- BM25 (키워드 검색) ----------

def build_bm25_index(chunks: list[dict]):
    """청크 리스트로 BM25 인덱스 구축"""
    tokenized_corpus = [tokenize_english(c["text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    return bm25


def search_bm25(bm25: BM25Okapi, chunks: list[dict], query: str, top_k: int = 5) -> list[dict]:
    """BM25로 키워드 기반 검색"""
    tokenized_query = tokenize_english(query)
    scores = bm25.get_scores(tokenized_query)
    ranked_indices = scores.argsort()[::-1][:top_k]
    return [chunks[i] for i in ranked_indices]


# ---------- 벡터 임베딩 (의미 기반 검색) ----------

def build_vector_store(chunks: list[dict], persist_directory: str = "chroma_db"):
    """청크 리스트로 벡터 스토어 구축 (디스크에 저장됨)"""
    documents = [
        Document(page_content=c["text"], metadata={"source": c["source"]})
        for c in chunks
    ]
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory,
    )
    return vector_store


def search_vector(vector_store, query: str, top_k: int = 5) -> list[dict]:
    """벡터 유사도로 의미 기반 검색"""
    results = vector_store.similarity_search(query, k=top_k)
    return [{"text": doc.page_content, "source": doc.metadata["source"]} for doc in results]


# ---------- 하이브리드 검색 ----------

def hybrid_search(bm25, chunks, vector_store, query: str, top_k: int = 5) -> list[dict]:
    """BM25 결과와 벡터 결과를 합쳐서(중복 제거) 반환"""
    bm25_results = search_bm25(bm25, chunks, query, top_k=top_k)
    vector_results = search_vector(vector_store, query, top_k=top_k)

    combined = {}
    for r in bm25_results:
        combined[r["text"]] = r
    for r in vector_results:
        combined.setdefault(r["text"], r)

    return list(combined.values())

import os


def load_or_build_vector_store(chunks: list[dict], persist_directory: str = "chroma_db"):
    """이미 저장된 벡터 스토어가 있으면 불러오고, 없으면 새로 만듦"""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if os.path.exists(persist_directory):
        return Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    return build_vector_store(chunks, persist_directory=persist_directory)

