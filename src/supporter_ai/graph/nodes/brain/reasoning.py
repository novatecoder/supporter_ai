import json
import logging
import redis.asyncio as redis
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, messages_from_dict, messages_to_dict
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

# Redis 클라이언트 초기화
redis_client = redis.Redis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT, 
    decode_responses=True
)

def get_llm():
    """반복 방지 및 토큰 최적화 설정 적용"""
    return ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        openai_api_base=settings.VLLM_URL,
        openai_api_key="EMPTY",
        temperature=0.7,
        model_kwargs={
            "presence_penalty": 0.6,
            "frequency_penalty": 0.5,
            "extra_body": {"repetition_penalty": 1.1}
        }
    )

# --- [에러 해결: 누락되었던 로드 노드 추가] ---
async def load_context_node(state: SupporterState):
    """Redis에서 과거 기록(messages)과 요약본(summary)을 불러옵니다."""
    session_id = state.get("session_id", "default")
    raw_data = await redis_client.get(f"supporter:context:{session_id}")
    if raw_data:
        data = json.loads(raw_data)
        return {
            "messages": messages_from_dict(data.get("messages", [])),
            "summary": data.get("summary", "")
        }
    return {"messages": [], "summary": ""}

async def summarize_node(state: SupporterState):
    """
    2048 토큰 제한을 엄격히 준수하는 요약 로직
    """
    history = state.get("messages", [])
    
    # 메시지가 5개 이상일 때 요약 실행
    if len(history) < 5:
        return {"messages": history}

    llm = get_llm()
    existing_summary = state.get("summary", "")
    
    # 요약할 텍스트 길이 엄격 제한 (2048 토큰 대응)
    history_str = str(history[:-2])
    if len(history_str) > 1500:
        history_str = "...(중략)... " + history_str[-1500:]

    summarize_prompt = f"""
    우리의 대화 기억: {existing_summary if existing_summary else "없음"}
    추가 내용: {history_str} 
    
    위 내용을 한 문장으로 아주 짧게 요약해줘.
    """
    
    try:
        response = await llm.ainvoke([HumanMessage(content=summarize_prompt)])
        return {
            "summary": response.content,
            "messages": history[-2:] # 요약 후 최근 대화만 남김
        }
    except Exception as e:
        logger.error(f"요약 실패: {e}")
        return {"messages": history[-2:]}

class BrainNode:
    async def __call__(self, state: SupporterState):
        llm = get_llm()
        pac = state.get("emotion_state", {}).get("pac_state", "A")
        summary = state.get("summary", "")
        history = state.get("messages", [])
        current_input = state.get("input", "")

        system_prompt = f"너는 서포터 AI야. 자아:{pac}. 기억:{summary if summary else '없음'}. 다정한 반말로 대답해."
        
        # 2048 제한을 위해 최근 2개 메시지만 과거 문맥으로 사용
        context_messages = history[-2:]
        full_messages = (
            [SystemMessage(content=system_prompt)] + 
            context_messages + 
            [HumanMessage(content=current_input)]
        )
        
        try:
            response = await llm.ainvoke(full_messages)
            return {"messages": [response]}
        except Exception as e:
            logger.warning(f"답변 생성 실패: {e}. 긴급 모드로 전환합니다.")
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt), 
                HumanMessage(content=current_input)
            ])
            return {"messages": [response]}

async def save_context_node(state: SupporterState):
    """현재 질문과 AI의 답변을 Redis에 저장 (TTL 1시간)"""
    session_id = state.get("session_id", "default")
    history = state.get("messages", [])
    current_input = state.get("input", "")
    
    # 새로운 히스토리 구성
    new_history = history + [HumanMessage(content=current_input), state["messages"][-1]]
    
    # 2048 제한을 위해 Redis에는 최근 6개까지만 유지
    data = {
        "messages": messages_to_dict(new_history[-6:]),
        "summary": state.get("summary", "")
    }
    await redis_client.setex(f"supporter:context:{session_id}", 3600, json.dumps(data))
    return state