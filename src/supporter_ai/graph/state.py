from typing import Annotated, List, TypedDict, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class SupporterState(TypedDict):
    # 과거 대화 기록 (최근 것만 유지됨)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 사용자의 현재 입력 (누락 방지용)
    input: str
    
    # 요약된 장기 기억
    summary: Optional[str]
    
    # 세션 및 상태 정보
    user_id: str
    session_id: str
    permissions: Dict[str, bool]
    sensory_data: Dict[str, Any]
    emotion_state: Dict[str, Any]