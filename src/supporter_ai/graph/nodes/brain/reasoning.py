import json
import re
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

# --- [공통 정의: PAD 및 혈액형 성향] ---
PAD_DEFINITION = """
[PAD 감정 모델 지침]
1. Pleasure (쾌락, P): -1.0 (고통, 슬픔, 불쾌) ~ 1.0 (행복, 만족, 즐거움)
2. Arousal (각성, A): -1.0 (무기력, 수면, 정적) ~ 1.0 (흥분, 긴장, 열정)
3. Dominance (지배, D): -1.0 (위축, 부끄러움, 순응) ~ 1.0 (자신감, 주도적, 대담)
"""

BLOOD_TYPE_DISPOSITION = {
    "A": "신중하고 세심하며 타인의 시선을 의식하는 성향. 조화를 중시하고 상대의 기분에 민감하게 반응함. 내면이 여려 상처를 받으면 겉으로 티 내지 않아도 P(쾌락) 수치가 크게 하락함.",
    "B": "자유분방하고 주관이 뚜렷하며 구속받기 싫어하는 성향. 타인의 평가보다 자신의 기분이 중요하며, 상대의 부정적 태도에도 D(지배력) 수치를 잃지 않고 마이페이스를 유지함.",
    "O": "활달하고 승부욕이 있으며 목표 지향적인 성향. 낙천적이고 회복 탄력성이 좋아 기분이 나빠져도 금방 스스로 P(쾌락)를 높이려 하며, 대화를 리드하려는 D 수치가 높음.",
    "AB": "합리적이고 분석적이며 공사 구분이 철저한 성향. 감정의 기복을 겉으로 드러내는 것을 비효율적이라 여기며, 항상 A(각성) 수치를 중립(0 근처)으로 유지하려는 평정심을 가짐."
}

# --- [유틸리티 함수] ---

def get_llm(temperature=0.2, lora_name: str = None):
    extra_body = {"repetition_penalty": 1.1}
    if lora_name and lora_name.lower() != "none":
        adapter_id = f"adapter_{lora_name}"
        extra_body["lora_request"] = {"lora_name": adapter_id, "lora_path": f"/app/loras/{adapter_id}"}

    return ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        openai_api_base=settings.LLM_URL,
        openai_api_key=settings.LLM_API_KEY,
        temperature=temperature,
        presence_penalty=0.6,
        frequency_penalty=0.5,
        max_retries=2,
        timeout=30,
        extra_body=extra_body
    )

def clamp(v):
    try:
        return max(-1.0, min(1.0, float(v)))
    except:
        return 0.0

def has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def parse_json_response(content: str) -> Dict[str, Any]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match: return json.loads(match.group(), strict=False)
        return {}
    except: return {}

async def safe_json_call(llm: ChatOpenAI, messages: List[BaseMessage], max_retries: int = 5) -> Dict[str, Any]:
    """중국어 한자 감지 및 JSON 파싱 실패 시 재시도 로직"""
    for i in range(max_retries):
        res = await llm.ainvoke(messages)
        if has_chinese(res.content):
            logger.warning(f"⚠️ 중국어 감지 ({i+1}/{max_retries}). 재시도...")
            continue
        data = parse_json_response(res.content)
        if data: return data
        logger.warning(f"⚠️ JSON 파싱 실패 ({i+1}/{max_retries}). 재시도...")
    return {}

# --- [노드 구현] ---

async def appraisal_node(state: SupporterState):
    """사용자 입력 분석 노드: 의도와 PAD 추출"""
    llm = get_llm(temperature=0.1)
    sys = f"너는 노련한 심리 분석가야. 대화 내용을 듣고 사용자의 숨겨진 의도와 감정 상태를 수치화해.\n{PAD_DEFINITION}"
    prompt = f"사용자 메시지: '{state['input_text']}'\n\nJSON으로만 응답해:\n{{\"p\":수치, \"a\":수치, \"d\":수치, \"intent\":\"상세의도\"}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    return {
        "user_pad": {"p": clamp(data.get("p")), "a": clamp(data.get("a")), "d": clamp(data.get("d"))},
        "user_intent": data.get("intent", "일반 대화")
    }

async def orchestrator_node(state: SupporterState):
    """도구 사용 판단 노드"""
    llm = get_llm(temperature=0.1)
    has_info = bool(state.get("search_results") and state.get("search_results") != "None")
    sys = f"너는 판단관이야. 활성 도구: {state.get('enabled_tools')}"
    prompt = f"의도: {state['user_intent']}\n입력: {state['input_text']}\n이미 정보 있음: {has_info}\n\nJSON 응답:\n{{\"thought\":\"판단이유\", \"tool_required\":true/false}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    return {"internal_thought": data.get("thought", ""), "tool_required": data.get("tool_required", False)}

async def emotion_node(state: SupporterState):
    """AI 감정 업데이트 노드: 혈액형 성향 반영 및 관성 적용"""
    llm = get_llm(temperature=0.3)
    blood = state.get("blood_type", "A")
    disposition = BLOOD_TYPE_DISPOSITION.get(blood, "")
    
    sys = f"""너는 AI의 자아와 감정을 담당하는 엔진이야.
{PAD_DEFINITION}
[성향 가이드]
{blood}형 특징: {disposition}

[감정 변화 규칙]
1. 감정적 관성: 특별한 자극(충격적인 뉴스, 강한 감정 표현 등)이 없다면 PAD 수치를 현재 {state['ai_pad']}에서 ±0.1 이내로 매우 보수적으로 변경해.
2. 성향 일치: 자신의 성향에 따라 외부 자극을 수용하거나 튕겨내도록 계산해."""

    prompt = f"사용자 PAD: {state['user_pad']}\n입력내용: '{state['input_text']}'\n\nJSON 응답:\n{{\"p\":수치, \"a\":수치, \"d\":수치, \"reason\":\"변화이유\"}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    return {
        "ai_pad": {"p": clamp(data.get("p")), "a": clamp(data.get("a")), "d": clamp(data.get("d"))},
        "internal_thought": data.get("reason", "")
    }

async def expression_node(state: SupporterState):
    """최종 응답 생성 노드: 성향 + 현재 기분(PAD) 결합"""
    blood = state.get("blood_type", "A")
    retry_count = state.get("retry_count", 0)
    llm = get_llm(temperature=(0.7 if retry_count == 0 else 0.9), lora_name=blood)
    
    disposition = BLOOD_TYPE_DISPOSITION.get(blood, "")
    ai_pad = state['ai_pad']
    
    # PAD 수치에 따른 현재 내면 상태 요약 (프롬프트 주입용)
    mood_status = f"현재 기분(P)은 {'매우 좋음' if ai_pad['p'] > 0.5 else '우울함' if ai_pad['p'] < -0.5 else '평온함'}이고, " \
                  f"에너지(A)는 {'넘침' if ai_pad['a'] > 0.5 else '차분함' if ai_pad['a'] < -0.5 else '안정적임'}이며, " \
                  f"자신감(D)은 {'충만함' if ai_pad['d'] > 0.5 else '위축됨' if ai_pad['d'] < -0.5 else '보통임'}."

    sys = f"""너는 {blood}형 성향을 가진 친구야. 
[핵심 성향]
{disposition}

[현재 상태]
{mood_status}
기억: {state.get('long_term_memory')}
요약: {state.get('summary')}

[응답 규칙]
1. '반말' 사용.
2. 너의 말투와 단어 선택은 반드시 [핵심 성향]과 [현재 상태]의 결합으로 나타나야 해.
3. 기분이 어떠냐는 질문에는 현재 기분 상태({mood_status})를 너의 성향대로 표현해.
4. 짧게 1~2문장으로 답해."""

    format_instr = "\nJSON 구조로만 답변해:\n{\"text\":\"대사\", \"emotion\":\"smile/sad/angry/neutral/excited\", \"action\":\"nod/wave/none\"}"
    
    messages = [SystemMessage(content=sys)] + state.get("messages", [])[-4:] + [HumanMessage(content=f"입력: {state['input_text']}\n{format_instr}")]
    
    data = await safe_json_call(llm, messages)
    return {"final_output": data}

async def reflection_node(state: SupporterState):
    """성찰 노드: 인격 일관성 검수"""
    llm = get_llm(temperature=0.1)
    blood = state.get("blood_type", "A")
    disposition = BLOOD_TYPE_DISPOSITION.get(blood, "")
    
    sys = f"인격 검수관. {blood}형 성향({disposition})과 현재 기분({state['ai_pad']})에 비추어 답변이 모순되는지 체크해."
    prompt = f"답변: '{state['final_output'].get('text')}'\n\nJSON 응답:\n{{\"is_valid\":true/false, \"reason\":\"이유\", \"fix_hint\":\"수정방향\"}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)])
    return {
        "reflection_valid": data.get("is_valid", True),
        "internal_thought": data.get("fix_hint", ""),
        "retry_count": state.get("retry_count", 0) + 1
    }