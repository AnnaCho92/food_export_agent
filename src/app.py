from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes import extraction_node

builder = StateGraph(AgentState)
builder.add_node("extraction", extraction_node)
builder.add_edge(START, "extraction")
builder.add_edge("extraction", END)
graph = builder.compile()