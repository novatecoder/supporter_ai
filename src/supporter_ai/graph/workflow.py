from langgraph.graph import StateGraph, END
from supporter_ai.graph.state import SupporterState
from supporter_ai.graph.nodes.brain.reasoning import BrainNode

async def create_supporter_workflow(checkpointer):
    """
    Redis Stack 기반의 비동기 체크포인터를 사용하여 대화를 영구 저장합니다.
    """
    workflow = StateGraph(SupporterState)

    # 노드 등록
    workflow.add_node("brain", BrainNode())

    # 시작점 및 엣지 설정
    workflow.set_entry_point("brain")
    workflow.add_edge("brain", END)

    # 컴파일 (Redis Saver 적용)
    return workflow.compile(checkpointer=checkpointer)