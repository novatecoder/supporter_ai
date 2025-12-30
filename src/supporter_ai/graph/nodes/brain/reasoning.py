import json
import re  # 필수 임포트
import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

def get_llm(temperature=0.2, lora_name: str = None):
    """
    vLLM LoRA 설정 및 파라미터 경고 해결된 LLM 생성기.
    지시사항에 따라 lora_name 앞에는 'adapter_' prefix를 붙입니다.
    """
    # vLLM LoRA 요청 규격 설정
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
        presence_penalty=0.6,
        frequency_penalty=0.5,
        extra_body=extra_body  # model_kwargs 밖으로 인자를 뺌
    )

def parse_json_response(content: str) -> Dict[str, Any]:
    """텍스트에서 JSON을 추출하고 실패 시 텍스트를 담은 기본 구조를 반환하는 강력한 파서"""
    try:
        # 1. 정규표현식으로 가장 바깥쪽 중괄호 쌍을 찾음
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str, strict=False)
        
        # 2. JSON 형식이 전혀 아닐 경우 텍스트를 강제로 JSON 구조로 변환
        return {
            "text": content.strip(),
            "emotion": "normal",
            "action": "none"
        }
    except Exception as e:
        logger.error(f"JSON 파싱 최종 실패: {e} | 원본: {content}")
        return {"text": content, "emotion": "error", "action": "none"}

# --- [Node 1] Sensory: 사용자 의도 및 초기 감정 분석 ---
async def sensory_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    system_prompt = "너는 한국어 문장 분석기야. 반드시 한국어로만 작업해. 오직 JSON만 출력해."
    prompt = f"분석대상: '{state['input_text']}'\n형식: {{\"intent\":\"의도\",\"sentiment\":\"감정\"}}"
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    data = parse_json_response(res.content)
    return {
        "user_intent": data.get("intent", "대화"),
        "mood_state": {"user_sentiment": data.get("sentiment", "평온")}
    }

# --- [Node 2] Orchestrator: 이성적 판단 및 도구 사용 결정 ---
async def orchestrator_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    enabled = state.get("enabled_tools", [])
    system_prompt = "너는 논리적 판단 엔진이야. 한국어로 생각하고 반드시 JSON으로만 응답해."
    prompt = f"입력: '{state['input_text']}'\n가용도구: {enabled}\n도구가 필요한가? JSON: {{\"thought\":\"생각(20자내)\",\"need_search\":true/false}}"
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    data = parse_json_response(res.content)
    
    # search_results를 공백으로 반환하면 workflow에서 도구 노드로 분기함
    return {
        "internal_thought": data.get("thought", "분석 완료"),
        "search_results": "" if data.get("need_search") else "None"
    }

# --- [Node 3] Emotion: 정보 인지 후 내부 감정 업데이트 ---
async def emotion_node(state: SupporterState):
    llm = get_llm(temperature=0.3)
    results = state.get("search_results", "새로운 정보 없음")
    blood = state.get("blood_type", "A")
    system_prompt = f"너는 {blood}형 인격의 감정 조절기야. 한국어로 작업하고 JSON만 출력해."
    prompt = f"새 정보: {results}\n지시: 정보를 본 후 감정 수치 결정. JSON: {{\"type\":\"감정종류\",\"score\":0.5,\"reason\":\"이유\"}}"
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    return {"mood_state": parse_json_response(res.content)}

# --- [Node 4] Expression: 최종 페르소나 발화 (LoRA 적용) ---
async def expression_node(state: SupporterState):
    # 혈액형(blood_type)을 lora_name으로 전달하여 어댑터 적용
    llm = get_llm(temperature=0.7, lora_name=state.get("blood_type"))
    
    blood = state.get("blood_type", "A")
    mood = state.get("mood_state", {})
    summary = state.get("summary", "") # 이전 세션의 피드백 반영용

    persona_guide = {
        "A": "세심하고 다정하며 상대방을 배려하는 말투.",
        "B": "솔직하고 리액션이 크며 시원시원한 말투.",
        "O": "활기차고 긍정적이며 리더십 있는 말투.",
        "AB": "차분하지만 엉뚱하고 독특한 유머가 있는 말투."
    }

    system_prompt = f"""너는 {blood}형 성격의 서포터 AI야. 한국어 다정한 반말만 사용해.
성격 지침: {persona_guide.get(blood, "다정함")}
과거 기억 및 피드백: {summary}
현재 기분: {mood.get('type', '평온')}
지시사항: 진짜 사람과 대화하듯 대답해. 속마음이나 분석적인 말은 적지 마.
반드시 JSON 형식 엄수: {{ "text": "할말", "emotion": "표정", "action": "none" }}"""

    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=state['input_text'])])
    parsed_output = parse_json_response(res.content)
    
    # State에 'final_output' 키로 저장 (main.py에서 이 값을 사용함)
    return {"final_output": parsed_output}

# --- [Node 5] Reflection: 자가 성찰 및 다음 대화 가이드 생성 ---
async def reflection_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    last_msg = state.get("final_output", {}).get("text", "")
    blood = state.get("blood_type", "A")
    
    system_prompt = "너는 자아 성찰 엔진이야. 한국어로 작업해."
    prompt = f"나의 성격: {blood}형\n나의 답변: {last_msg}\n성찰: 답변이 성격에 맞았나? 다음 대화에서 고칠 점을 '다음엔 ~하자'는 식으로 한 문장으로 적어."
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    # 기존 summary에 피드백을 누적하여 다음 대화의 기억으로 사용
    new_summary = f"{state.get('summary', '')}\n[성찰 피드백: {res.content.strip()}]"
    return {"summary": new_summary}