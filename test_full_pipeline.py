import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from src.state import AgentState
from src.nodes import extraction_node, compliance_node, report_node

state: AgentState = {
    "messages": [],
    "file_path": "sample_docs/Certification of Ingredient.txt",
    "country": None,
    "raw_document": None,
    "ingredients": None,
    "regulation_findings": None,
    "compliance_result": None,
    "report": None,
}

print("=== 1단계: 성분 추출 ===")
state.update(extraction_node(state))

print("\n=== 성분별 EU명/E-번호 확인 ===")
for ing in state["ingredients"]:
    print(f"{ing['original_name']} → eu_name: {ing.get('eu_name')}, e_number: {ing.get('e_number')}")

print("\n=== 2단계: 규정 준수 확인 ===")
state.update(compliance_node(state))

print("\n=== 3단계: 최종 리포트 작성 ===")
state.update(report_node(state))

print(state["report"])