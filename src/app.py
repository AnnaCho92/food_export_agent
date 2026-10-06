from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes import extraction_node, compliance_node, report_node, save_result_node

builder = StateGraph(AgentState)

builder.add_node("extraction", extraction_node)
builder.add_node("compliance", compliance_node)
builder.add_node("report", report_node)
builder.add_node("save_result", save_result_node)

builder.add_edge(START, "extraction")
builder.add_edge("extraction", "compliance")
builder.add_edge("compliance", "report")
builder.add_edge("report", "save_result")
builder.add_edge("save_result", END)

graph = builder.compile()