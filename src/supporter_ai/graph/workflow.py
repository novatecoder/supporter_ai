from langgraph.graph import StateGraph, END, START
from supporter_ai.graph.state import SupporterState
from supporter_ai.graph.nodes.brain.reasoning import (
    load_context_node, 
    summarize_node, # 추가
    BrainNode, 
    save_context_node
)

async def create_supporter_workflow():
    workflow = StateGraph(SupporterState)

    # 노드 등록
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("summarize", summarize_node) # 추가
    workflow.add_node("brain", BrainNode())
    workflow.add_node("save_context", save_context_node)

    # 최적화된 흐름 설정
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "summarize") # 로드 후 바로 요약/정리
    workflow.add_edge("summarize", "brain")        # 정리된 상태로 답변 생성
    workflow.add_edge("brain", "save_context")     # 답변 후 Redis 저장
    workflow.add_edge("save_context", END)

    return workflow.compile()