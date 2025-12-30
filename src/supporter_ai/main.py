import traceback
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

from supporter_ai.graph.workflow import create_supporter_workflow
from supporter_ai.common.config import settings

# 앱 상태 공유
app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Supporter AI 하이브리드 엔진 로딩 중...")
        # 랭그래프 워크플로우 생성 및 컴파일
        app_state["graph"] = await create_supporter_workflow()
        yield 
    except Exception as e:
        logger.error(f"❌ 엔진 초기화 실패: {traceback.format_exc()}")
        raise e
    finally:
        app_state.clear()

app = FastAPI(title="Supporter AI API", lifespan=lifespan)

# 클라이언트 요청 규격
class ChatRequest(BaseModel):
    user_id: str = "kwh_01"
    session_id: str = "sess_01"
    message: str = "안녕"
    blood_type: Optional[str] = "A"               # 세션 설정값
    enabled_tools: Optional[List[str]] = []        # 활성화 도구 플래그
    disabled_tools: Optional[List[str]] = []

@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    graph = app_state.get("graph")
    if not graph:
        raise HTTPException(status_code=503, detail="시스템 로딩 중")

    # 그래프 시작 상태 설정 (state.py 규격 준수)
    initial_state = {
        "input_text": req.message,
        "user_id": req.user_id,
        "session_id": req.session_id,
        "blood_type": req.blood_type,
        "enabled_tools": req.enabled_tools,
        "disabled_tools": req.disabled_tools,
        "messages": [] # load_memory_node에서 채워질 예정
    }

    try:
        # 랭그래프 실행
        final_state = await graph.ainvoke(initial_state)
        
        # [수정 포인트] expression_node에서 생성된 'final_output'을 추출
        # response 필드가 비어있지 않도록 확실하게 매핑합니다.
        ai_response = final_state.get("final_output")
        
        # 만약 어떤 이유로든 final_output이 없으면 방어적으로 생성
        if not ai_response or not isinstance(ai_response, dict):
            ai_response = {
                "text": "미안해, 대답을 완성하지 못했어. 다시 말해줄래?",
                "emotion": "sad",
                "action": "none"
            }

        # 클라이언트 디버깅용 메타데이터 구성
        metadata = {
            "blood_type": final_state.get("blood_type"),
            "mood": final_state.get("mood_state"),
            "thought": final_state.get("internal_thought"),
            "search_results": final_state.get("search_results"),
            "summary": final_state.get("summary"),
            "active_tools": final_state.get("enabled_tools")
        }

        # 성공 응답 반환
        return {
            "status": "success", 
            "response": ai_response,  # 이 데이터가 demo_app의 메시지로 출력됨
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"❌ 채팅 실행 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("supporter_ai.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=settings.DEBUG)