from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter


def load_markdown_chunks(file_path: str, source_name: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
    """이미 LlamaParse로 파싱해둔 마크다운 파일을 읽어서 청킹"""
    with open(file_path, "r", encoding="utf-8") as f:
        full_markdown = f.read()

    splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(full_markdown)

    return [{"text": chunk, "source": source_name} for chunk in chunks]


def build_all_chunks() -> list[dict]:
    """네 개 규정 문서를 청킹해서 하나의 청크 리스트로 합침"""
    additive_chunks = load_markdown_chunks(
        "sample_docs/llama_md/General for Additives.md",
        source_name="식품첨가물 규정 (EC 1333/2008)",
        chunk_size=800,       # 표가 적어서 좀 더 작게
        chunk_overlap=100,
    )
    spec_chunks = load_markdown_chunks(
        "sample_docs/llama_md/Specifications for Additives.md",
        source_name="식품첨가물 상세내역 규정 (EU 231/2012)",
        chunk_size=1500,      # 표가 많아서 더 크게
        chunk_overlap=150,
    )
    labelling_chunks = load_markdown_chunks(
        "sample_docs/llama_md/Labelling.md",
        source_name="식품 라벨링 규정 (EU 1169/2011)",
        chunk_size=800,       # 조항 위주, 표 적음
        chunk_overlap=100,
    )
    contaminants_chunks = load_markdown_chunks(
        "sample_docs/llama_md/Contaminants.md",
        source_name="식품 오염물질 규정 (EU 2023/915)",
        chunk_size=1500,      # 오염물질별 허용기준 표가 많음
        chunk_overlap=150,
    )
    return additive_chunks + spec_chunks + labelling_chunks + contaminants_chunks