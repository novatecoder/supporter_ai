import json
import logging
import redis.asyncio as redis
from supporter_ai.common.config import settings
from supporter_ai.graph.state import SupporterState
from langchain_core.messages import messages_from_dict, messages_to_dict

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)

async def load_memory_node(state: SupporterState):
    session_id = state.get("session_id", "default")
    
    # Redis에서 세션 데이터 로드 (기록 + 설정)
    raw_data = await redis_client.get(f"supporter:context:{session_id}")
    
    if raw_data:
        data = json.loads(raw_data)
        # 1. 저장된 설정이 있으면 사용, 없으면 현재 요청(state)의 값을 사용
        blood_type = data.get("blood_type", state.get("blood_type", "A"))
        enabled_tools = data.get("enabled_tools", state.get("enabled_tools", ["google_search"]))
        disabled_tools = data.get("disabled_tools", state.get("disabled_tools", []))
        
        return {
            "messages": messages_from_dict(data.get("messages", [])),
            "summary": data.get("summary", ""),
            "blood_type": blood_type,
            "enabled_tools": enabled_tools,
            "disabled_tools": disabled_tools
        }
    
    # 데이터가 없는 신규 세션일 경우 기본값 반환
    return state

async def save_memory_node(state: SupporterState):
    session_id = state.get("session_id", "default")
    
    # 설정값과 대화 기록을 함께 저장
    data = {
        "messages": messages_to_dict(state["messages"][-6:]),
        "summary": state.get("summary", ""),
        "blood_type": state.get("blood_type"),        # 지속성을 위해 저장
        "enabled_tools": state.get("enabled_tools"),  # 지속성을 위해 저장
        "disabled_tools": state.get("disabled_tools") # 지속성을 위해 저장
    }
    
    await redis_client.setex(f"supporter:context:{session_id}", 3600, json.dumps(data))
    return state