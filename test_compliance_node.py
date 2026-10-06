import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from src.state import AgentState
from src.nodes import extraction_node, compliance_node

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
extraction_result = extraction_node(state)
state["ingredients"] = extraction_result["ingredients"]
print(f"추출된 성분 수: {len(state['ingredients'])}")

print("\n=== 2단계: 규정 준수 확인 ===")
compliance_result = compliance_node(state)

print("\n=== 최종 결과 ===")
for r in compliance_result["compliance_result"]["ingredients"]:
    status = "✅ 허용" if r["is_compliant"] else "❌ 위반/제한"
    print(f"{status} | {r['ingredient_name']} ({r['e_number'] or 'N/A'})")
    print(f"   근거: {r['notes']}")