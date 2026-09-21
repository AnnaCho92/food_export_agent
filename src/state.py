from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict) :
    messages: Annotated[list, add_messages]
    country: Optional[str]
    raw_document: Optional[str]
    ingredients: Optional[list]
    regulation_findings: Optional[list]
    compliance_result: Optional[dict]
    report: Optional[str]

    