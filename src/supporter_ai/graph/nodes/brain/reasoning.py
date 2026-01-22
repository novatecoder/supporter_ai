import json
import re
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

# --- [공통 정의: PAD 지침 경량화] ---
PAD_DEFINITION = "[PAD] P:쾌락(-1~1), A:각성(-1~1), D:지배(-1~1)"

BLOOD_TYPE_DISPOSITION = {
    "A": "신중, 세심, 타인 의식, 조화 중시, 내면 여림.",
    "B": "자유분방, 주관 뚜렷, 마이페이스 유지.",
    "O": "활달, 승부욕, 회복탄력성 높음, 대화 주도.",
    "AB": "합리적, 분석적, 공사 구분, 평정심 유지."
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
        max_retries=2,
        timeout=60,
        extra_body=extra_body
    )

def clamp(v):
    try: return max(-1.0, min(1.0, float(v)))
    except: return 0.0

def parse_json_response(content: str) -> Dict[str, Any]:
    try:
        # 마크다운 코드 블록(```json)이 섞여있어도 내용물만 추출
        content = content.replace("```json", "").replace("```", "").strip()
        
        # 가장 바깥쪽 중괄호 {} 사이의 내용을 찾음
        match = re.search(r"(\{.*\})", content, re.DOTALL)
        if match:
            return json.loads(match.group(1), strict=False)
        return {}
    except:
        return {}

async def safe_json_call(llm: ChatOpenAI, messages: List[BaseMessage], node_name: str, max_retries: int = 3) -> Dict[str, Any]:
    """JSON 파싱 실패나 호출 에러 발생 시 모델의 응답 원문을 로그에 포함합니다."""
    for i in range(max_retries):
        try:
            res = await llm.ainvoke(messages)
            data = parse_json_response(res.content)
            
            if data: 
                return data
            
            # JSON 파싱은 실패했지만 응답은 온 경우: 원문 출력
            logger.warning(f"⚠️ [{node_name}] 파싱 실패 ({i+1}/{max_retries}). 원문: {res.content}...")
            
        except Exception as e:
            # API 호출 자체가 실패한 경우
            logger.error(f"❌ [{node_name}] 호출 에러: {str(e)}")
            
    return {}

# --- [노드 구현: 토큰 최적화 및 간결화] ---

async def appraisal_node(state: SupporterState):
    """사용자 입력 분석: 의도와 PAD 추출"""
    llm = get_llm(temperature=0.1)
    # 지시사항을 간결하게 압축
    sys = f"심리 분석가. JSON으로만 응답. 마크다운 금지.\n{PAD_DEFINITION}"
    prompt = f"분석 대상: '{state['input_text']}'\n형식: {{\"p\":수치, \"a\":수치, \"d\":수치, \"intent\":\"한 문장 요약\"}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)], "AppraisalNode")
    return {
        "user_pad": {"p": clamp(data.get("p")), "a": clamp(data.get("a")), "d": clamp(data.get("d"))},
        "user_intent": data.get("intent", "일반 대화")
    }

async def orchestrator_node(state: SupporterState):
    """도구 사용 판단"""
    llm = get_llm(temperature=0.1)
    has_info = bool(state.get("search_results") and state.get("search_results") != "None")
    sys = "도구 판단관. JSON으로만 응답. 마크다운 금지."
    prompt = f"의도: {state['user_intent']}\n이미 정보 있음: {has_info}\n형식: {{\"thought\":\"이유(짧게)\", \"tool_required\":true/false}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)], "OrchestratorNode")
    return {"internal_thought": data.get("thought", ""), "tool_required": data.get("tool_required", False)}

async def emotion_node(state: SupporterState):
    """AI 감정 업데이트"""
    llm = get_llm(temperature=0.3)
    blood = state.get("blood_type", "A")
    disposition = BLOOD_TYPE_DISPOSITION.get(blood, "")
    
    sys = f"감정 엔진. 성향: {disposition}\nJSON으로만 응답. 마크다운 금지.\n{PAD_DEFINITION}"
    prompt = f"현재 PAD: {state['ai_pad']}\n사용자 PAD: {state['user_pad']}\n형식: {{\"p\":수치, \"a\":수치, \"d\":수치, \"reason\":\"짧은 요약\"}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)], "EmotionNode")
    return {
        "ai_pad": {"p": clamp(data.get("p")), "a": clamp(data.get("a")), "d": clamp(data.get("d"))},
        "internal_thought": data.get("reason", "")
    }

async def expression_node(state: SupporterState):
    """최종 응답 생성"""
    blood = state.get("blood_type", "A")
    retry_count = state.get("retry_count", 0)
    llm = get_llm(temperature=(0.7 if retry_count == 0 else 0.9), lora_name=blood)
    
    disposition = BLOOD_TYPE_DISPOSITION.get(blood, "")
    ai_pad = state['ai_pad']
    mood = f"P:{ai_pad['p']:.1f}, A:{ai_pad['a']:.1f}, D:{ai_pad['d']:.1f}"

    sys = f"너는 {blood}형 친구({disposition})야. 현재 기분({mood}) 반영. 반말로 짧게 답해. JSON 응답. 마크다운 금지."
    
    messages = [SystemMessage(content=sys)] + state.get("messages", [])[-4:]
    messages.append(HumanMessage(content=f"입력: {state['input_text']}\n형식: {{\"text\":\"대사\", \"emotion\":\"smile/sad/angry/neutral\", \"action\":\"nod/none\"}}"))
    
    data = await safe_json_call(llm, messages, "ExpressionNode")
    return {"final_output": data}

async def reflection_node(state: SupporterState):
    """성찰 노드: 일관성 검수"""
    llm = get_llm(temperature=0.1)
    blood = state.get("blood_type", "A")
    disposition = BLOOD_TYPE_DISPOSITION.get(blood, "")
    
    sys = "인격 검수관. JSON 응답. 마크다운 금지."
    prompt = f"성향: {disposition}\n상태: {state['ai_pad']}\n답변: '{state['final_output'].get('text')}'\n형식: {{\"is_valid\":true/false, \"reason\":\"짧은 이유\", \"fix_hint\":\"간결한 방향\"}}"
    
    data = await safe_json_call(llm, [SystemMessage(content=sys), HumanMessage(content=prompt)], "ReflectionNode")
    return {
        "reflection_valid": data.get("is_valid", True),
        "internal_thought": data.get("fix_hint", ""),
        "retry_count": state.get("retry_count", 0) + 1
    }