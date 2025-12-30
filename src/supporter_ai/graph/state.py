from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator

class SupporterState(TypedDict):
    # 1. 세션 및 환경
    session_id: str
    user_id: str
    blood_type: str            # A, B, O, AB 플래그
    enabled_tools: List[str]   # 활성화된 기능 리스트
    disabled_tools: List[str]  # 비활성화된 기능 리스트
    
    # 2. 입력 및 메모리
    input_text: str
    messages: Annotated[List[BaseMessage], operator.add]
    summary: str
    
    # 3. 중간 분석 결과 (Logic 노드들이 생성)
    user_intent: str           # 사용자의 의도
    mood_state: Dict[str, Any] # 현재 감정 { "type": "happy", "score": 0.8 }
    search_results: str        # 도구가 가져온 지식
    internal_thought: str      # 브레인의 사고 과정
    
    # 4. 최종 출력
    final_output: Dict[str, Any] # { "text": "...", "emotion": "...", "action": "..." }