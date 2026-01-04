# src/supporter_ai/graph/nodes/tools/memory.py
import json
import logging
import redis.asyncio as redis
from typing import List
from supporter_ai.common.config import settings
from supporter_ai.graph.state import SupporterState
from langchain_core.messages import messages_from_dict, messages_to_dict, HumanMessage, AIMessage, SystemMessage
from supporter_ai.graph.nodes.brain.reasoning import get_llm, safe_json_call, parse_json_response
from supporter_ai.common.db_utils import search_memory_db, save_memory_to_db

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)

async def load_memory_node(state: SupporterState):
    """DB/Redis에서 상태를 로드하는 로직 노드"""
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", "default")
    
    raw_data = await redis_client.get(f"supporter:context:{session_id}")
    short_term_msgs = []
    summary = ""
    ai_pad = state.get("ai_pad", {"p": 0.0, "a": 0.0, "d": 0.0})
    
    if raw_data:
        data = json.loads(raw_data)
        short_term_msgs = messages_from_dict(data.get("messages", []))
        summary = data.get("summary", "")
        ai_pad = data.get("ai_pad", ai_pad)

    ltm_context = await search_memory_db(user_id, [0.0]*1024)

    return {
        "messages": short_term_msgs,
        "summary": summary,
        "ai_pad": ai_pad,
        "long_term_memory": ltm_context,
        "blood_type": state.get("blood_type") or (data.get("blood_type") if raw_data else "A"),
        "retry_count": 0 # 매 턴마다 카운트 초기화
    }

async def update_history_node(state: SupporterState):
    """메시지 이력을 업데이트하는 로직 노드"""
    messages = state.get("messages", [])
    new_user_msg = HumanMessage(content=state["input_text"])
    new_ai_msg = AIMessage(content=state.get("final_output", {}).get("text", ""))
    return {"messages": messages + [new_user_msg, new_ai_msg]}

async def summarize_node(state: SupporterState):
    """중요도를 판별하고 요약하는 노드 (JSON 파싱 재시도 필요)"""
    messages = state.get("messages", [])
    if len(messages) < 6: return {}

    llm = get_llm(temperature=0.1)
    sys = "기억 전략가. 대화 요약 및 중요도(0-10) 판별."
    prompt = f"대상: {messages[-4:]}\n형식: {{\"summary\":\"요약\", \"importance\":8, \"key_fact\":\"사실\"}}"

    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    
    importance = int(data.get("importance", 0))
    if importance >= 7 and data.get("key_fact"):
        await save_memory_to_db(state["user_id"], data["key_fact"], [0.0]*1024, float(importance/10))
        logger.info(f"💾 중요 기억 저장: {data['key_fact']}")

    return {
        "summary": data.get("summary", state.get("summary", "")),
        "messages": messages[-4:]
    }

async def save_memory_node(state: SupporterState):
    """최종 상태를 Redis에 저장하는 로직 노드"""
    session_id = state.get("session_id", "default")
    data = {
        "messages": messages_to_dict(state["messages"]), 
        "summary": state.get("summary", ""),
        "blood_type": state.get("blood_type"),
        "ai_pad": state.get("ai_pad")
    }
    await redis_client.setex(f"supporter:context:{session_id}", 3600, json.dumps(data))
    return state