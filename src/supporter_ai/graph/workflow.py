from langgraph.graph import StateGraph, END, START
from supporter_ai.graph.state import SupporterState
from supporter_ai.graph.nodes.tools.memory import load_memory_node, save_memory_node
from supporter_ai.graph.nodes.tools.gateway import tool_gateway_node
from supporter_ai.graph.nodes.brain.reasoning import (
    sensory_node, 
    orchestrator_node, 
    emotion_node, 
    expression_node, 
    reflection_node
)

async def create_supporter_workflow():
    workflow = StateGraph(SupporterState)

    # 1. 모든 노드 등록
    workflow.add_node("load_memory", load_memory_node)      # 메모리 로드 (Code)
    workflow.add_node("sensory_analyze", sensory_node)     # 의도 분석 (Logic)
    workflow.add_node("orchestrator", orchestrator_node)   # 도구 사용 판단 (Logic)
    workflow.add_node("tool_gateway", tool_gateway_node)   # 도구 실행 (Code)
    workflow.add_node("emotion_update", emotion_node)      # 감정 업데이트 (Logic)
    workflow.add_node("expression", expression_node)       # 최종 응답 생성 (Persona)
    workflow.add_node("save_memory", save_memory_node)     # 저장 및 요약 (Code)
    workflow.add_node("reflection", reflection_node)       # 자가 성찰 (Background Logic)

    # 2. 기본 흐름 연결
    workflow.add_edge(START, "load_memory")
    workflow.add_edge("load_memory", "sensory_analyze")
    workflow.add_edge("sensory_analyze", "orchestrator")
    
    # 3. 조건부 엣지: 도구가 필요하면 gateway로, 아니면 바로 감정 단계로
    workflow.add_conditional_edges(
        "orchestrator",
        lambda x: "tool" if x.get("tool_required") else "no_tool",
        {
            "tool": "tool_gateway",
            "no_tool": "emotion_update"
        }
    )
    
    # 도구 실행 후 다시 오케스트레이터로 돌아가서 추가 작업이 필요한지 확인 (루프)
    workflow.add_edge("tool_gateway", "orchestrator")
    
    # 감정 업데이트 -> 표현 생성 -> 저장 -> 성찰 -> 종료
    workflow.add_edge("emotion_update", "expression")
    workflow.add_edge("expression", "save_memory")
    workflow.add_edge("save_memory", "reflection")
    workflow.add_edge("reflection", END)

    return workflow.compile()