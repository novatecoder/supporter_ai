# src/supporter_ai/graph/state.py
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class SupporterState(TypedDict):
    """
    Supporter AI의 전체 상태를 관리하는 객체입니다.
    스탠퍼드 AI 마을의 기억 구조와 PAD 감정 모델을 지원합니다.
    """
    
    # 1. 세션 및 환경 정보
    session_id: str
    user_id: str
    blood_type: str              # A, B, O, AB 페르소나 설정
    enabled_tools: List[str]     # 활성화된 도구 (검색 등)
    disabled_tools: List[str]    # 비활성화된 도구
    
    # 2. 감정 상태 (PAD 모델: Pleasure, Arousal, Dominance)
    # 각 수치는 -1.0(부정/차분/위축)에서 1.0(긍정/흥분/지배) 사이의 값을 가집니다.
    ai_pad: Dict[str, float]     # AI의 현재 감정 수치 {'p': 0.0, 'a': 0.0, 'd': 0.0}
    user_pad: Dict[str, float]   # 사용자의 최신 입력 감정 수치 {'p': 0.0, 'a': 0.0, 'd': 0.0}
    
    # 3. 입력 및 기억 (Memory)
    input_text: str              # 사용자의 최신 메시지
    messages: List[BaseMessage]  # 최근 대화 이력 (Redis 기반 단기 기억)
    summary: str                 # 이전 대화들의 요약본 (Context)
    long_term_memory: str        # PostgreSQL(pgvector)에서 검색된 관련 과거 기억/지식
    importance_score: float      # 현재 대화의 중요도 (0.0 ~ 1.0, AI 마을 저장 기준)
    
    # 4. 분석 및 중간 사고 결과
    user_intent: str             # 사용자의 의도 분석 결과
    search_results: str          # 외부 도구 실행 결과 (검색 데이터 등)
    internal_thought: str        # 에이전트의 내부 추론/생각 과정
    
    # 5. 최종 출력 및 액션
    # 형식: { "text": "안녕!", "emotion": "smile", "action": "wave_hand" }
    final_output: Dict[str, Any]

    # 6. 워크플로우 제어 (중요!)
    reflection_valid: bool       # 성찰 통과 여부 (True면 다음 단계로, False면 재시도)
    retry_count: int             # 무한 루프 방지를 위한 재시도 카운터
    tool_required: bool          # 도구 사용 필요 여부