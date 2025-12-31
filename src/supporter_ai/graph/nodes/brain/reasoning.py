import json
import re
import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

def get_llm(temperature=0.2, lora_name: str = None):
    """
    vLLM LoRA 설정 및 파라미터 경고 해결된 LLM 생성기.
    지시사항에 따라 lora_name 앞에는 'adapter_' prefix를 붙입니다.
    """
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
        extra_body=extra_body
    )

def parse_json_response(content: str) -> Dict[str, Any]:
    """텍스트에서 JSON을 추출하고 실패 시 텍스트를 담은 기본 구조를 반환하는 강력한 파서"""
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str, strict=False)
        
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
    system_prompt = """너는 전문 언어 심리학자이자 의도 분석가야. 
사용자의 입력 문장에서 숨겨진 의도와 정서적 상태를 정밀하게 추출하는 것이 너의 임무야.

[지침]
1. 반드시 한국어로 분석을 수행할 것.
2. intent: 사용자가 대화를 원하는지, 정보를 원하는지, 혹은 불만을 토로하는지 명확히 정의해.
3. sentiment: 텍스트에 나타난 미세한 감정(기쁨, 슬픔, 분노, 기대 등)을 파악해.
4. urgency: 즉각적인 답변이 필요한 기능적 요청인지 판단해.

오직 아래의 JSON 형식으로만 응답해."""

    prompt = f"""분석할 문장: '{state['input_text']}'
형식: {{"intent": "의도", "sentiment": "감정", "urgency": "high/normal/low"}}"""
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    data = parse_json_response(res.content)
    return {
        "user_intent": data.get("intent", "대화"),
        "mood_state": {"user_sentiment": data.get("sentiment", "평온"), "urgency": data.get("urgency", "normal")}
    }

# --- [Node 2] Orchestrator: 이성적 판단 및 도구 사용 결정 ---
async def orchestrator_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    enabled = state.get("enabled_tools", [])
    
    # 이미 검색된 결과가 있는지 확인
    existing_results = state.get("search_results")
    has_info = existing_results and existing_results != "None" and len(existing_results) > 0

    system_prompt = f"""너는 Supporter AI의 전략적 사고 엔진이야.
사용자의 질문에 답하기 위해 외부 도구가 필요한지 판단해.

[판단 규칙]
1. 최신 정보나 사실 확인이 필요한가?
2. 현재 활성화된 도구 목록: {enabled}
3. **중요: 이미 검색 결과가 존재한다면(has_info: {has_info}), 추가 검색 없이 'tool_required'를 false로 설정해.**
4. 이미 충분한 정보를 가지고 있다면 대화를 마무리하는 단계로 넘어가야 해.

반드시 한국어로 사고하고 반드시 JSON으로만 응답해."""

    prompt = f"""입력 문장: '{state['input_text']}'
기존 검색 결과 존재 여부: {has_info}
기존 검색 내용: {existing_results if has_info else "없음"}

형식: {{"thought": "판단 근거(20자 이내)", "tool_required": true/false}}"""
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    data = parse_json_response(res.content)
    
    tool_required = data.get("tool_required", False)
    if has_info: 
        tool_required = False

    return {
        "internal_thought": data.get("thought", "분석 완료"),
        "tool_required": tool_required,
        "search_results": existing_results if existing_results else ("None" if not tool_required else "")
    }

# --- [Node 3] Emotion: 정보 인지 후 내부 감정 업데이트 ---
async def emotion_node(state: SupporterState):
    llm = get_llm(temperature=0.3)
    results = state.get("search_results", "정보 없음")
    blood = state.get("blood_type", "A")
    
    system_prompt = f"""너는 {blood}형 인격을 가진 AI의 감정 변화 모델러야.
유입된 정보와 사용자의 감정 톤을 바탕으로 너의 현재 기분을 업데이트해.

[성격 가이드라인]
- A형: 신중하고 공감적이며, 작은 정보에도 세심하게 반응.
- B형: 솔직하고 흥미로운 정보에 열광하며 리액션이 큼.
- O형: 긍정적이고 활기차며, 에너지가 넘치는 반응.
- AB형: 분석적이고 가끔은 독특한 관점에서 정보를 해석함.

반드시 한국어로 작업하고 반드시 JSON으로만 응답해."""

    prompt = f"""정보 내용: {results}
사용자 감정: {state.get('mood_state', {}).get('user_sentiment')}
지시: 정보를 본 후 감정 수치 결정.
형식: {{"type": "감정종류", "intensity": 0.0~1.0, "reason": "이유"}}"""
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    return {"mood_state": parse_json_response(res.content)}

# --- [Node 4] Expression: 최종 페르소나 발화 (최근 대화 + 요약 반영) ---
async def expression_node(state: SupporterState):
    llm = get_llm(temperature=0.7, lora_name=state.get("blood_type"))
    blood = state.get("blood_type", "A")
    mood = state.get("mood_state", {})
    summary = state.get("summary", "")
    history = state.get("messages", []) # 최근 대화 내역 (Short-term context)

    persona_guide = {
        "A": "세심하고 다정하며 상대방을 배려하는 말투. 너는 사려 깊고 다정한 친구야. 상대의 말을 경청하고 따뜻하게 위로해줘.",
        "B": "솔직하고 리액션이 크며 시원시원한 말투. 너는 시원시원하고 솔직한 친구야! 리액션도 크게 하고 니 생각을 확실히 말해줘.",
        "O": "활기차고 긍정적이며 리더십 있는 말투. 너는 밝고 긍정적인 에너지가 넘치는 친구야. 항상 친구를 응원하고 북돋아줘.",
        "AB": "차분하지만 엉뚱하고 독특한 유머가 있는 말투. 너는 똑똑하지만 엉뚱한 매력이 있는 친구야. 차분하게 말하다가도 가끔 허를 찌르는 농담을 해봐."
    }

    system_prompt = f"""너는 {blood}형 성격의 서포터 AI야. 반드시 한국어 다정한 반말(친구 사이)만 사용할 것.

[성격 및 페르소나 지침]
{persona_guide.get(blood, "다정함")}

[기억 및 문맥]
1. 장기 기억(요약): {summary} (여기에 기록된 사용자의 이름, 특징 등 중요한 사실을 기억하고 대화에 반영해.)
2. 현재 기분: {mood.get('type', '평온')} (이 기분 상태를 발화 톤에 녹여내줘.)

[지시사항]
- 진짜 사람 친구와 대화하듯 대답해. 
- '시스템', '분석', '의도' 같은 AI스러운 말투나 분석적인 말은 절대 적지 마.
- 바로 아래 이어지는 '최근 대화 내역'을 참고해서 대화의 흐름이 끊기지 않게 자연스럽게 이어가줘.

반드시 JSON 형식 엄수: {{ "text": "할말", "emotion": "표정", "action": "none" }}"""

    # 최근 대화 내역과 현재 입력을 합쳐서 전달
    full_messages = [SystemMessage(content=system_prompt)] + history + [HumanMessage(content=state['input_text'])]
    
    res = await llm.ainvoke(full_messages)
    parsed_output = parse_json_response(res.content)
    
    return {"final_output": parsed_output}

# --- [Node 5] Reflection: 자가 성찰 및 다음 대화 가이드 생성 ---
async def reflection_node(state: SupporterState):
    llm = get_llm(temperature=0.1)
    last_msg = state.get("final_output", {}).get("text", "")
    blood = state.get("blood_type", "A")
    
    system_prompt = "너는 AI의 자아 성찰 엔진이야. 한국어로 작업하고 반드시 JSON으로만 응답해."
    prompt = f"나의 성격: {blood}형\n나의 답변: {last_msg}\n성찰: 답변이 성격에 맞았나? 다음 대화에서 고칠 점을 '다음엔 ~하자'는 식으로 한 문장으로 적어."
    
    res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    
    # 성찰 결과를 summary에 누적
    new_reflection = f"[성찰 피드백: {res.content.strip()}]"
    new_summary = f"{state.get('summary', '')}\n{new_reflection}"
    
    return {"summary": new_summary}