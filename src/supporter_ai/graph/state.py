from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class SupporterState(TypedDict):
    """서포터 AI의 전체 추론 상태를 관리합니다."""
    
    messages: Annotated[List[BaseMessage], add_messages]
    emotion_state: Dict[str, Any]
    personality: Dict[str, Any]
    sensory_data: Dict[str, Any]
    
    # 제어 권한 (Permissions)
    permissions: Dict[str, bool]
    
    user_id: str
    session_id: str
    
    next_step: Optional[str]
    error: Optional[str]
    retry_count: int