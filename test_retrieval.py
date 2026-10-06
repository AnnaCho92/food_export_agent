import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from src.load_split import build_all_chunks
from src.retrieval import build_bm25_index, build_vector_store, hybrid_search

print("청크 생성 중...")
chunks = build_all_chunks()
print(f"총 {len(chunks)}개 청크")

print("BM25 인덱스 구축 중...")
bm25 = build_bm25_index(chunks)

print("벡터 스토어 구축 중... (임베딩 API 호출, 시간이 좀 걸릴 수 있어요)")
vector_store = build_vector_store(chunks)

query = "E160c"
print(f"\n검색어: {query}")
results = hybrid_search(bm25, chunks, vector_store, query, top_k=3)

for r in results:
    print(f"[{r['source']}]")
    print(r["text"][:200])
    print("---")

# --- 진단: E160c 관련 청크가 실제로 몇 등인지 확인 ---
target_index = None
for i, c in enumerate(chunks):
    if "capsanthin" in c["text"].lower():
        target_index = i
        break

if target_index is None:
    print("capsanthin이 포함된 청크를 못 찾았습니다 (청킹 과정에서 소실된 것 같습니다)")
else:
    print(f"\n'capsanthin' 포함 청크 인덱스: {target_index}")
    print(f"해당 청크 길이: {len(chunks[target_index]['text'])}자")
    print(f"해당 청크 내용 미리보기: {chunks[target_index]['text'][:300]}")

    from src.retrieval import tokenize_english
    tokenized_query = tokenize_english("E160c")
    print(f"\n정규화된 검색어 토큰: {tokenized_query}")

    all_scores = bm25.get_scores(tokenized_query)
    target_score = all_scores[target_index]
    rank = (all_scores > target_score).sum() + 1
    print(f"해당 청크의 BM25 점수: {target_score}")
    print(f"전체 {len(chunks)}개 중 순위: {rank}등")