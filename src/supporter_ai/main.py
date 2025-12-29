import traceback
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from loguru import logger

from supporter_ai.graph.workflow import create_supporter_workflow
from supporter_ai.graph.nodes.brain.reasoning import redis_client
from supporter_ai.common.config import settings

app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Supporter AI 초기화 (커스텀 노드 + 요약 시스템)")
        app_state["graph"] = await create_supporter_workflow()
        yield 
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {traceback.format_exc()}")
        raise e
    finally:
        app_state.clear()

app = FastAPI(title="Supporter AI", lifespan=lifespan)

class ChatRequest(BaseModel):
    user_id: str = "kwh_01"
    session_id: str = "sess_01"
    message: str = "안녕"

@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    graph = app_state.get("graph")
    if not graph:
        raise HTTPException(status_code=503, detail="시스템 로딩 중")

    # [수정] 현재 질문은 input 필드에, 기록은 messages에 분리
    initial_state = {
        "input": req.message,
        "messages": [], # 로드 노드에서 채워질 예정
        "user_id": req.user_id,
        "session_id": req.session_id,
        "permissions": {"allow_vision": False},
        "sensory_data": {},
        "emotion_state": {"pac_state": "A"}
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        
        # 데모 페이지 익스팬더를 위한 메타데이터 구성
        metadata = {
            "pac_state": final_state.get("emotion_state", {}).get("pac_state"),
            "summary": final_state.get("summary", "기억 없음"),
            "history_count": len(final_state.get("messages", []))
        }

        return {
            "status": "success", 
            "response": final_state["messages"][-1].content,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"❌ 채팅 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("supporter_ai.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=settings.DEBUG)