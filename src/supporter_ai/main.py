# src/supporter_ai/main.py
import traceback
import uvicorn
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from supporter_ai.graph.workflow import create_supporter_workflow
from supporter_ai.common.config import settings
from supporter_ai.common.db_utils import init_db  # 추가된 임포트

# 앱 상태 공유
app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 DB 초기화 및 랭그래프 엔진 로딩"""
    try:
        logger.info("🚀 Supporter AI 하이브리드 엔진 로딩 중...")
        
        # 1. DB 및 Qdrant 컬렉션 초기화 (여기서 컬렉션이 생성됩니다)
        await init_db() 
        
        # 2. 랭그래프 워크플로우 생성 및 컴파일
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
    blood_type: Optional[str] = "A"
    enabled_tools: Optional[List[str]] = []
    disabled_tools: Optional[List[str]] = []

async def run_post_processing(graph, state: Dict[str, Any]):
    try:
        summary = state.get("summary", "")
        if summary:
            logger.info(f"✅ 백그라운드 요약 완료: {summary[:30]}...")
    except Exception as e:
        logger.error(f"❌ 사후 처리 중 오류 발생: {e}")

@app.post("/api/v1/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    graph = app_state.get("graph")
    if not graph:
        raise HTTPException(status_code=503, detail="시스템 로딩 중")

    initial_state = {
        "input_text": req.message,
        "user_id": req.user_id,
        "session_id": req.session_id,
        "blood_type": req.blood_type,
        "enabled_tools": req.enabled_tools,
        "disabled_tools": req.disabled_tools,
        "messages": [],
        "ai_pad": {"p": 0.0, "a": 0.0, "d": 0.0} # 초기 PAD값 설정
    }

    try:
        final_state = await graph.ainvoke(
            initial_state, 
            config={"recursion_limit": 50}
        )
        
        ai_response = final_state.get("final_output")
        if not ai_response or not isinstance(ai_response, dict):
            ai_response = {
                "text": "미안해, 대답을 준비하는 중에 문제가 생겼어. 다시 말해줄래?",
                "emotion": "sad",
                "action": "none"
            }

        background_tasks.add_task(run_post_processing, graph, final_state)

        metadata = {
            "blood_type": final_state.get("blood_type"),
            "ai_pad": final_state.get("ai_pad"), # mood_state 대신 ai_pad 반환
            "thought": final_state.get("internal_thought"),
            "search_results": final_state.get("search_results"),
            "summary": final_state.get("summary"),
            "active_tools": final_state.get("enabled_tools")
        }

        return {
            "status": "success", 
            "response": ai_response,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"❌ 채팅 실행 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("supporter_ai.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=settings.DEBUG)