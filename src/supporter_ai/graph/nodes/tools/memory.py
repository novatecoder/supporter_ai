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
    messages = state.get("messages", [])
    if len(messages) <= 10:
        return {}

    llm = get_llm(temperature=0.1)
    # Prompt Diet: 핵심 정보 위주 압축
    sys = "기억 압축기. 한국어만 사용. 중국어 금지"
    prompt = f"""기존요약: {state.get("summary", "")}
추가내용: {messages[:-4]}
지침: 이름, 취향 등 팩트 위주로 100자 내 압축."""

    # 여기서도 중국어 체크 적용
    from supporter_ai.graph.nodes.brain.reasoning import safe_llm_call
    logger.warning(f"⚠️ summarize_node 시도 중...")
    content = await safe_llm_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    
    return {
        "summary": content.strip(),
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