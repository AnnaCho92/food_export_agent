from dotenv import load_dotenv
load_dotenv()

from src.state import AgentState
from src.nodes import extraction_node

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

result = extraction_node(state)

print("=== 추출된 성분 ===")
for ing in result["ingredients"]:
    print(ing)