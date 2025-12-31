# src/supporter_ai/graph/nodes/tools/memory.py
import json
import logging
import redis.asyncio as redis
from supporter_ai.common.config import settings
from supporter_ai.graph.state import SupporterState
from langchain_core.messages import messages_from_dict, messages_to_dict, HumanMessage, AIMessage, SystemMessage
from supporter_ai.graph.nodes.brain.reasoning import get_llm

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)

async def load_memory_node(state: SupporterState):
    session_id = state.get("session_id", "default")
    raw_data = await redis_client.get(f"supporter:context:{session_id}")
    if raw_data:
        data = json.loads(raw_data)
        return {
            "messages": messages_from_dict(data.get("messages", [])),
            "summary": data.get("summary", ""),
            "blood_type": state.get("blood_type") or data.get("blood_type", "A")
        }
    return state

async def update_history_node(state: SupporterState):
    """현재 턴의 대화를 메시지 리스트에 추가 (중복 방지를 위해 전체 리스트 구성)"""
    messages = state.get("messages", [])
    new_user_msg = HumanMessage(content=state["input_text"])
    new_ai_msg = AIMessage(content=state.get("final_output", {}).get("text", ""))
    
    # 리듀서가 없으므로 합쳐진 리스트를 반환하여 상태를 갱신함
    return {"messages": messages + [new_user_msg, new_ai_msg]}

async def summarize_node(state: SupporterState):
    """임계값 초과 시 요약 수행 및 메시지 리스트 비우기"""
    messages = state.get("messages", [])
    
    # 10개 이하일 때는 실행 안 함 (이때 디버그 로그가 안 찍힐 수 있음)
    if len(messages) <= 10:
        return {}

    logger.info(f"🚀 메시지 {len(messages)}개 도달. 요약을 시작합니다.")
    llm = get_llm(temperature=0.1)
    existing_summary = state.get("summary", "")
    
    summary_prompt = f"""너는 기억 관리자야. 토큰 제한을 위해 정보를 압축해.
[기존 요약]: {existing_summary}
[최신 대화]: {messages[:-4]}
지침: 이름과 핵심 취향은 절대 빼지 말고 200자 내외로 업데이트해."""

    res = await llm.ainvoke([SystemMessage(content="기억 압축 엔진"), HumanMessage(content=summary_prompt)])
    
    # 요약본을 갱신하고, 메시지 리스트는 최근 4개만 남겨서 '비워줌' (토큰 확보)
    return {
        "summary": res.content.strip(),
        "messages": messages[-4:] 
    }

async def save_memory_node(state: SupporterState):
    session_id = state.get("session_id", "default")
    data = {
        "messages": messages_to_dict(state["messages"]), 
        "summary": state.get("summary", ""),
        "blood_type": state.get("blood_type")
    }
    await redis_client.setex(f"supporter:context:{session_id}", 3600, json.dumps(data))
    logger.info(f"💾 세션 {session_id} 저장 완료.")
    return state