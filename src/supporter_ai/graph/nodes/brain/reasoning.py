# src/supporter_ai/graph/nodes/brain/reasoning.py
import json
import re
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

def get_llm(temperature=0.2, lora_name: str = None):
    # vLLM 전용 파라미터 (빈도 제어)
    extra_body = {"repetition_penalty": 1.1}
    
    if lora_name and lora_name.lower() != "none":
        adapter_id = f"adapter_{lora_name}"
        extra_body["lora_request"] = {
            "lora_name": adapter_id, 
            "lora_path": f"/app/loras/{adapter_id}"
        }

    return ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        openai_api_base=settings.LLM_URL,
        openai_api_key=settings.LLM_API_KEY,
        temperature=temperature,
        # 다시 추가된 파라미터들
        presence_penalty=0.6,   # 새로운 주제/단어 사용 유도
        frequency_penalty=0.5,  # 동일 단어 반복 방지
        max_retries=2,
        timeout=30,
        extra_body=extra_body
    )

def has_chinese(text: str) -> bool:
    """중국어 한자 포함 여부 확인"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

async def safe_llm_call(llm: ChatOpenAI, messages: List[BaseMessage], max_retries: int = 5) -> str:
    """중국어 발생 시 최대 5번 재시도하는 래퍼 함수"""
    for i in range(max_retries):
        res = await llm.ainvoke(messages)
        content = res.content
        if not has_chinese(content):
            return content
        logger.warning(f"⚠️ 중국어 감지됨 ({i+1}/{max_retries}). 재시도 중...")
    
    # 5번 모두 실패 시 중국어 제거 시도
    return re.sub(r'[\u4e00-\u9fff]', '', res.content)

def parse_json_response(content: str) -> Dict[str, Any]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match: return json.loads(match.group(), strict=False)
        return {"text": content.strip(), "emotion": "normal", "action": "none"}
    except Exception:
        return {"text": content, "emotion": "error", "action": "none"}

# --- [Node 1] Sensory ---
async def sensory_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    # Prompt Diet: 핵심 지시와 출력 형식만 정의
    sys = "의도/감정 분석가. 한국어만 사용. 중국어 금지. JSON 응답."
    prompt = f"입력: '{state['input_text']}'\n형식: {{\"intent\": \"의도\", \"sentiment\": \"감정\", \"urgency\": \"high/normal\"}}"
    logger.warning(f"⚠️ sensory_node 시도 중...")
    content = await safe_llm_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    data = parse_json_response(content)
    return {
        "user_intent": data.get("intent", "대화"),
        "mood_state": {"user_sentiment": data.get("sentiment", "평온"), "urgency": data.get("urgency", "normal")}
    }

# --- [Node 2] Orchestrator ---
async def orchestrator_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    has_info = bool(state.get("search_results") and state.get("search_results") != "None")
    
    # Prompt Diet: 근거는 짧게, 판단 위주
    sys = f"도구 사용 판단관. 사용 가능 도구: {state.get('enabled_tools')}. 한국어만 사용."
    prompt = f"입력: '{state['input_text']}'\n기존정보: {has_info}\n형식: {{\"thought\": \"판단근거(단문)\", \"tool_required\": true/false}}"
    logger.warning(f"⚠️ orchestrator_node 시도 중...")
    content = await safe_llm_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    data = parse_json_response(content)
    
    return {
        "internal_thought": data.get("thought", "분석완료"),
        "tool_required": False if has_info else data.get("tool_required", False)
    }

# --- [Node 3] Emotion ---
async def emotion_node(state: SupporterState):
    llm = get_llm(temperature=0.3)
    # Prompt Diet: 이유(reason)는 매우 짧게
    sys = f"{state.get('blood_type', 'A')}형 성격 모델러. 한국어만 사용."
    prompt = f"상황: {state.get('mood_state', {}).get('user_sentiment')}\n형식: {{\"type\": \"감정\", \"reason\": \"이유(단문)\"}}"
    logger.warning(f"⚠️ emotion_node 시도 중...")
    content = await safe_llm_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    return {"mood_state": parse_json_response(content)}

# --- [Node 4] Expression ---
async def expression_node(state: SupporterState):
    llm = get_llm(temperature=0.7, lora_name=state.get("blood_type"))
    blood = state.get("blood_type", "A")
    persona = {"A": "다정한", "B": "솔직한", "O": "밝은", "AB": "차분한"}.get(blood, "친절한")

    # [중요] 대화를 주고받도록 강제: 혼자 길게 말하지 말 것
    sys = f"""너는 {blood}형 {persona} 친구야. 
- 오직 한국어 반말만 사용. 중국어 절대 금지.
- 기억: {state.get('summary', '')}
- 규칙: 짧게 한두 문장으로만 말해. 혼자 길게 떠들지 말고 질문을 던지거나 리액션만 해. 대화를 이어가는 게 목적이야.
- 형식: {{ "text": "할말", "emotion": "표정" }}"""

    messages = [SystemMessage(content=sys)] + state.get("messages", []) + [HumanMessage(content=state['input_text'])]

    logger.warning(f"⚠️ expression_node 시도 중...")
    content = await safe_llm_call(llm, messages)
    return {"final_output": parse_json_response(content)}