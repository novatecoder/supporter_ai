# src/supporter_ai/graph/workflow.py
from langgraph.graph import StateGraph, END, START
from supporter_ai.graph.state import SupporterState
from supporter_ai.graph.nodes.tools.memory import (
    load_memory_node, save_memory_node, summarize_node, update_history_node
)
from supporter_ai.graph.nodes.tools.gateway import tool_gateway_node
from supporter_ai.graph.nodes.brain.reasoning import (
    sensory_node, orchestrator_node, emotion_node, expression_node, reflection_node
)

async def create_supporter_workflow():
    workflow = StateGraph(SupporterState)

    # 1. 모든 노드 등록
    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("sensory_analyze", sensory_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("tool_gateway", tool_gateway_node)
    workflow.add_node("emotion_update", emotion_node)
    workflow.add_node("expression", expression_node)
    workflow.add_node("update_history", update_history_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("save_memory", save_memory_node) # 마지막에 저장

    # 2. 엣지 연결
    workflow.add_edge(START, "load_memory")
    workflow.add_edge("load_memory", "sensory_analyze")
    workflow.add_edge("sensory_analyze", "orchestrator")
    
    workflow.add_conditional_edges(
        "orchestrator",
        lambda x: "tool" if x.get("tool_required") else "no_tool",
        {"tool": "tool_gateway", "no_tool": "emotion_update"}
    )
    workflow.add_edge("tool_gateway", "orchestrator")
    
    # [중요] 답변 생성 -> 기록 업데이트 -> 요약 -> 성찰 -> 저장 순서
    workflow.add_edge("emotion_update", "expression")
    workflow.add_edge("expression", "update_history")
    workflow.add_edge("update_history", "summarize")
    workflow.add_edge("summarize", "reflection")
    workflow.add_edge("reflection", "save_memory")
    workflow.add_edge("save_memory", END)

    return workflow.compile()