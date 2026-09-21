import json
from langchain_tavily import TavilySearch
from langchain.agents import create_agent
from src.prompts import EXTRACTION_SYSTEM_PROMPT
from src.state import AgentState


search_tool = TavilySearch(max_results=3)

extraction_agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[search_tool],
    system_prompt=EXTRACTION_SYSTEM_PROMPT,
)


def extraction_node(state: AgentState) -> dict:
    document_text = state["messages"][-1].content

    result = extraction_agent.invoke({
        "messages": [{"role": "user", "content": document_text}]
    })

    last_message = result["messages"][-1]
    raw_output = last_message.content

    try:
        ingredients = json.loads(raw_output)
    except json.JSONDecodeError:
        ingredients = []

    return {"ingredients": ingredients}