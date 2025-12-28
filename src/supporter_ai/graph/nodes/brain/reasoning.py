from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from supporter_ai.graph.state import SupporterState
from supporter_ai.common.config import settings

class BrainNode:
    def __init__(self):
        # Qwen2.5-VL-7B-Instruct-AWQ 기반 vLLM 연동
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            openai_api_key="EMPTY",
            openai_api_base=settings.VLLM_URL,
            temperature=0.7
        )

    async def __call__(self, state: SupporterState):
        perms = state.get("permissions", {})
        pac = state.get("emotion_state", {}).get("pac_state", "A")
        
        # 성격(PAC)과 인프라(Neo4j/Qdrant)를 인지하는 시스템 프롬프트
        system_prompt = f"""
        당신은 사용자의 든든한 조력자 '서포터 AI'입니다.
        
        현재 당신의 설정:
        - 자아 상태(PAC): {pac}
        - 권한: [검색: {'허용' if perms.get('allow_search') else '차단'}, 시각: {'허용' if perms.get('allow_vision') else '차단'}]
        
        연결된 외부 지능:
        1. Neo4j 지식 그래프: 사용자의 인맥과 사회적 관계를 이해하고 있습니다.
        2. Qdrant 벡터 기억: 사용자와의 과거 대화 에피소드를 소중히 기억하고 있습니다.
        
        작동 지침:
        - 사용자와의 친밀도를 바탕으로 간단하게 대답하세요.
        """
        
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        
        try:
            response = await self.llm.ainvoke(messages)
            return {
                "messages": [response],
                "next_step": "end",
                "retry_count": state.get("retry_count", 0) + 1
            }
        except Exception as e:
            return {"error": str(e), "next_step": "error"}