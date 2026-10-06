from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    file_path: Optional[str]
    country: Optional[str]
    product_id: Optional[int]
    raw_document: Optional[str]
    ingredients: Optional[list]
    regulation_findings: Optional[list]
    compliance_result: Optional[dict]
    report: Optional[str]
    report_data: Optional[dict]
    