# src/supporter_ai/main.py
import traceback
import uvicorn
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from langchain_core.messages import HumanMessage, AIMessage
from supporter_ai.graph.workflow import create_supporter_workflow
from supporter_ai.common.config import settings
from supporter_ai.common.db_utils import init_db

# 앱 상태 공유
app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 DB 초기화 및 랭그래프 엔진 로딩"""
    try:
        logger.info("🚀 Supporter AI (EXAONE Engine) 로딩 중...")
        await init_db() 
        app_state["graph"] = await create_supporter_workflow()
        yield 
    except Exception as e:
        logger.error(f"❌ 엔진 초기화 실패: {traceback.format_exc()}")
        raise e
    finally:
        app_state.clear()

app = FastAPI(title="Supporter AI API", lifespan=lifespan)

# [수정] 대화 기록(history)을 포함하도록 요청 모델 확장
class ChatRequest(BaseModel):
    user_id: str = "kwh_01"
    session_id: str = "sess_01"
    message: str = "안녕"
    blood_type: Optional[str] = "A"
    enabled_tools: Optional[List[str]] = []
    disabled_tools: Optional[List[str]] = []
    history: Optional[List[Dict[str, Any]]] = []
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

    # [수정] 프론트엔드에서 넘어온 history를 LangChain 메시지 객체로 변환
    formatted_messages = []
    for m in req.history:
        if m["role"] == "user":
            formatted_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            formatted_messages.append(AIMessage(content=m["content"]))

    initial_state = {
        "input_text": req.message,
        "user_id": req.user_id,
        "session_id": req.session_id,
        "blood_type": req.blood_type,
        "enabled_tools": req.enabled_tools,
        "disabled_tools": req.disabled_tools,
        "messages": formatted_messages, # 이전 대화 맥락 주입
        "ai_pad": {"p": 0.0, "a": 0.0, "d": 0.0} 
    }

    try:
        # 랭그래프 엔진 실행
        final_state = await graph.ainvoke(
            initial_state, 
            config={"recursion_limit": 50}
        )
        
        ai_response = final_state.get("final_output")
        
        # 응답이 없거나 JSON 파싱 실패 시 예외 처리
        if not ai_response or not isinstance(ai_response, dict):
            logger.error(f"❌ 최종 응답 생성 실패. 상태: {final_state.get('internal_thought')}")
            ai_response = {
                "text": "미안해, 대답을 준비하는 중에 문제가 생겼어. 다시 말해줄래?",
                "emotion": "sad",
                "action": "none"
            }

        background_tasks.add_task(run_post_processing, graph, final_state)

        return {
            "status": "success", 
            "response": ai_response,
            "metadata": {
                "blood_type": final_state.get("blood_type"),
                "ai_pad": final_state.get("ai_pad"),
                "thought": final_state.get("internal_thought"),
                "summary": final_state.get("summary"),
                "active_tools": final_state.get("enabled_tools")
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 채팅 실행 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("supporter_ai.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=settings.DEBUG)