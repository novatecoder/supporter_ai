# src/supporter_ai/graph/workflow.py
from langgraph.graph import StateGraph, END, START
from supporter_ai.graph.state import SupporterState
from supporter_ai.graph.nodes.tools.memory import (
    load_memory_node, save_memory_node, summarize_node, update_history_node
)
from supporter_ai.graph.nodes.tools.gateway import tool_gateway_node
from supporter_ai.graph.nodes.brain.reasoning import (
    appraisal_node, orchestrator_node, emotion_node, expression_node, reflection_node
)

# --- [라우팅 로직] ---

def route_after_orchestrator(state: SupporterState):
    """도구 사용 여부에 따른 분기"""
    if state.get("tool_required"):
        return "tool"
    return "no_tool"

def route_after_reflection(state: SupporterState):
    """성찰 결과 및 재시도 횟수에 따른 분기 (무한 루프 방지)"""
    if state.get("reflection_valid", True):
        return "pass"
    
    # 최대 2회까지만 재시도 허용 (retry_count는 0부터 시작)
    if state.get("retry_count", 0) <= 2:
        return "retry"
    
    return "pass" # 횟수 초과 시 강제 통과

async def create_supporter_workflow():
    workflow = StateGraph(SupporterState)

    # 노드 등록
    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("appraisal", appraisal_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("tool_gateway", tool_gateway_node)
    workflow.add_node("emotion_update", emotion_node)
    workflow.add_node("expression", expression_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("update_history", update_history_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("save_memory", save_memory_node) 

    # 엣지 연결
    workflow.add_edge(START, "load_memory")
    workflow.add_edge("load_memory", "appraisal")
    workflow.add_edge("appraisal", "orchestrator")
    
    # 1. 도구 분기
    workflow.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"tool": "tool_gateway", "no_tool": "emotion_update"}
    )
    workflow.add_edge("tool_gateway", "orchestrator")
    
    # 2. 감정 및 생성
    workflow.add_edge("emotion_update", "expression")
    workflow.add_edge("expression", "reflection")
    
    # 3. 검수 및 재시도 분기 (무한 루프 방지 핵심)
    workflow.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {"pass": "update_history", "retry": "expression"}
    )
    
    # 4. 마무리 로직
    workflow.add_edge("update_history", "summarize")
    workflow.add_edge("summarize", "save_memory")
    workflow.add_edge("save_memory", END)

    return workflow.compile()