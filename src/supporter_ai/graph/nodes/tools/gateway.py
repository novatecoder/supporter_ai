import logging
from supporter_ai.graph.state import SupporterState

logger = logging.getLogger(__name__)

async def tool_gateway_node(state: SupporterState):
    """실제 도구를 실행하거나 차단 메시지를 반환합니다."""
    # Orchestrator가 결정한 도구 이름 (예제에서는 단순화)
    # 실제로는 state에 tool_to_call 같은 필드를 추가하여 관리합니다.
    
    # 가상의 구글 검색 결과 시뮬레이션
    search_query = state.get("input_text")
    logger.info(f"도구 실행 시도: google_search | 쿼리: {search_query}")
    
    # 실제 구현 시 여기에 google_search_api 호출 로직이 들어갑니다.
    mock_result = f"'{search_query}'에 대한 검색 결과: 매우 긍정적이고 흥미로운 정보들."
    
    return {
        "search_results": mock_result,
        "tool_required": False # 실행 완료 후 루프 탈출을 위해 False로 설정
    }