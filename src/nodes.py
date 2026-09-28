from langchain.agents import create_agent
from src.prompts import EXTRACTION_SYSTEM_PROMPT
from src.state import AgentState
from src.tools import (
    ExtractionResult,
    extract_text_from_pdf,
    extract_text_from_txt,
    enrich_ingredient,
    save_product,
    save_ingredients,
)


extraction_agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[],
    system_prompt=EXTRACTION_SYSTEM_PROMPT,
    response_format=ExtractionResult,
)


def extraction_node(state: AgentState) -> dict:
    if state.get("file_path"):
        file_path = state["file_path"]
        print(f"[1/5] 파일에서 텍스트 추출 중: {file_path}")
        if file_path.endswith(".pdf"):
            document_text = extract_text_from_pdf(file_path)
        else:
            document_text = extract_text_from_txt(file_path)
        print(f"      텍스트 추출 완료 ({len(document_text)}자)")
    else:
        document_text = state["messages"][-1].content

    print("[2/5] 문서에서 제품/성분 정보 추출 중...")
    result = extraction_agent.invoke({
        "messages": [{"role": "user", "content": document_text}]
    })
    extracted: ExtractionResult = result["structured_response"]
    print(f"      성분 {len(extracted.ingredients)}개 추출 완료")

    print("[3/5] 성분별 EU 표준명/E-number 조회 중... (성분마다 몇 초씩 걸려요)")
    for i, item in enumerate(extracted.ingredients, start=1):
        print(f"      ({i}/{len(extracted.ingredients)}) {item.original_name} 조회 중...")
        enrichment = enrich_ingredient(item.original_name)
        item.eu_name = enrichment.eu_name
        item.e_number = enrichment.e_number

    print("[4/5] DB에 제품 정보 저장 중...")
    product_id = save_product(extracted.product)

    print(f"[5/5] DB에 성분 {len(extracted.ingredients)}개 저장 중...")
    save_ingredients(product_id, extracted.ingredients)
    print("      완료!")

    return {
        "raw_document": document_text,
        "ingredients": [item.model_dump() for item in extracted.ingredients],
    }