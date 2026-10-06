from langchain.agents import create_agent
from src.prompts import EXTRACTION_SYSTEM_PROMPT, COMPLIANCE_SYSTEM_PROMPT
from src.state import AgentState
from src.tools import (
    ExtractionResult,
    extract_text_from_pdf,
    extract_text_from_txt,
    enrich_ingredient,
    save_product,
    save_ingredients,
    get_country_id, 
    save_export_request_and_result
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
        "product_id": product_id,
        "ingredients": [item.model_dump() for item in extracted.ingredients],
    }


from pydantic import BaseModel
from typing import Optional

from src.compliance_tools import search_regulation
from src.prompts import COMPLIANCE_SYSTEM_PROMPT


class IngredientComplianceResult(BaseModel):
    ingredient_name: str
    e_number: Optional[str] = None
    is_compliant: bool
    max_usage_level: Optional[str] = None
    notes: str


compliance_agent = create_agent(
    model="gpt-4o-mini",
    tools=[search_regulation],
    system_prompt=COMPLIANCE_SYSTEM_PROMPT,
    response_format=IngredientComplianceResult,
)


def check_ingredient_compliance(ingredient: dict) -> dict:
    """성분 1개에 대해 독립적으로 규정 준수 여부를 판단 (격리된 호출)"""
    name = ingredient.get("eu_name") or ingredient["original_name"]
    query = f"성분명: {name}, E-번호: {ingredient.get('e_number') or '없음'}"
    result = compliance_agent.invoke({"messages": [{"role": "user", "content": query}]})
    compliance_dict = result["structured_response"].model_dump()
    compliance_dict["original_name"] = ingredient["original_name"]
    compliance_dict["allergen_category"] = ingredient.get("allergen_category")
    return compliance_dict


def compliance_node(state: AgentState) -> dict:
    ingredients = state["ingredients"]
    results = []
    for i, ing in enumerate(ingredients, 1):
        display_name = ing.get("eu_name") or ing["original_name"]
        print(f"[Compliance {i}/{len(ingredients)}] {display_name} 규정 확인 중...")
        results.append(check_ingredient_compliance(ing))
    return {"compliance_result": {"ingredients": results}}

from src.tools import generate_export_report


def report_node(state: AgentState) -> dict:
    print("[Report] 최종 리포트 작성 중...")
    compliance_results = state["compliance_result"]["ingredients"]
    report = generate_export_report(compliance_results)

    verdict = "✅ 수출 가능" if report.is_exportable else "❌ 수출 불가"
    report_text = f"""
=== EU 수출 가능 여부 최종 리포트 ===

{verdict}

[요약]
{report.summary}
"""
    if report.violations:
        report_text += "\n[규정 위반 성분]\n"
        for v in report.violations:
            report_text += f"- {v}\n"

    if report.recommendations:
        report_text += "\n[권장 조치]\n"
        for r in report.recommendations:
            report_text += f"- {r}\n"

    # --- 라벨링 주의사항: AI 판단이 아니라 이미 추출된 데이터로 직접 계산 ---
    allergen_ingredients = [
        r for r in compliance_results if r.get("allergen_category")
    ]
    if allergen_ingredients:
        report_text += "\n[⚠ 라벨링 주의사항 - 알레르기 유발 성분]\n"
        report_text += "EU 라벨링 규정(1169/2011)에 따라 아래 성분은 제품 라벨에 " \
                        "굵게(bold) 표시해야 합니다:\n"
        for r in allergen_ingredients:
            report_text += f"- **{r['original_name']}** (알레르기 유발물질: {r['allergen_category']})\n"

    print("[Report] 완료!")
    return {"report": report_text, "report_data": report.model_dump()}

def save_result_node(state: AgentState) -> dict:
    country_name = state.get("country")
    if not country_name:
        print("[Save] 수출 대상 국가가 지정되지 않아 DB 저장을 건너뜁니다.")
        return {}

    print(f"[Save] 검토 결과를 DB에 저장 중... (대상 국가: {country_name})")
    country_id = get_country_id(country_name)
    data = state["report_data"]

    risk_level = "LOW" if data["is_exportable"] else "HIGH"
    recommendation = "\n".join(data["recommendations"]) or "해당 없음"

    request_id = save_export_request_and_result(
        product_id=state["product_id"],
        country_id=country_id,
        risk_level=risk_level,
        result_summary=state["report"],
        recommendation=recommendation,
    )
    print(f"[Save] 저장 완료! (request_id: {request_id})")
    return {}