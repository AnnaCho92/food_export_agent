from langchain_core.tools import tool

from src.load_split import build_all_chunks
from src.retrieval import build_bm25_index, load_or_build_vector_store, hybrid_search


_chunks = None
_bm25 = None
_vector_store = None


def _ensure_knowledge_base():
    """규정 지식베이스가 아직 준비 안 됐으면 준비 (최초 1회만 실행됨)"""
    global _chunks, _bm25, _vector_store
    if _chunks is None:
        print("[Compliance] 규정 지식베이스 로딩 중...")
        _chunks = build_all_chunks()
        _bm25 = build_bm25_index(_chunks)
        _vector_store = load_or_build_vector_store(_chunks)
        print(f"[Compliance] 지식베이스 준비 완료 ({len(_chunks)}개 청크)")


@tool
def search_regulation(query: str) -> str:
    """EU 식품 첨가물 규정(1333/2008, 231/2012)에서 관련 내용을 검색합니다.
    성분명, E-번호(예: E160c), 최대 사용량, 허용 여부 등을 물어볼 때 사용하세요."""
    _ensure_knowledge_base()
    results = hybrid_search(_bm25, _chunks, _vector_store, query, top_k=3)
    return "\n\n---\n\n".join(
        f"[출처: {r['source']}]\n{r['text']}" for r in results
    )