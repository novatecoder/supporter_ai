import traceback
import redis.asyncio as redis # Redis 상태 체크를 위해 추가
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from loguru import logger
from langgraph.checkpoint.redis.aio import AsyncRedisSaver 

from supporter_ai.graph.workflow import create_supporter_workflow
from supporter_ai.common.config import settings

# 전역 상태 관리
app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 Redis 연결 및 워크플로우 초기화"""
    try:
        logger.info("🚀 Supporter AI 초기화 (Redis Stack 연결 중...)")
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        
        # 1. Redis 상태 체크용 클라이언트 (Health check용)
        app_state["redis_client"] = redis.from_url(redis_url, decode_responses=True)
        
        # 2. Async 컨텍스트 매니저로 LangGraph 체크포인터 관리
        async with AsyncRedisSaver.from_conn_string(redis_url) as saver:
            app_state["graph"] = await create_supporter_workflow(saver)
            logger.info("✅ Redis Stack 연결 및 워크플로우 로드 완료.")
            yield 
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {traceback.format_exc()}")
        raise e
    finally:
        # 종료 시 연결 정리
        if "redis_client" in app_state:
            await app_state["redis_client"].aclose()
        app_state.clear()

app = FastAPI(title="Supporter AI", lifespan=lifespan)

# --- [SECTION: 데이터 모델] ---
class ChatRequest(BaseModel):
    user_id: str = "kwh_01"
    session_id: str = "sess_01"
    message: str = "안녕" # 기본 예시값

# --- [SECTION: API 엔드포인트] ---

@app.get("/health")
async def health_check():
    """
    서버 상태 및 주요 컴포넌트(Redis, AI Engine) 연결 확인
    """
    graph_ready = "graph" in app_state
    redis_ready = False
    
    try:
        # Redis PING 테스트
        if "redis_client" in app_state:
            redis_ready = await app_state["redis_client"].ping()
    except Exception:
        redis_ready = False

    return {
        "status": "healthy" if graph_ready and redis_ready else "unhealthy",
        "project": "Supporter AI",
        "engine_ready": graph_ready,
        "redis_connected": redis_ready,
        "model": settings.LLM_MODEL_NAME #
    }

@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    """AI와 채팅을 수행하는 엔드포인트"""
    graph = app_state.get("graph")
    if not graph:
        raise HTTPException(status_code=503, detail="AI 엔진 로드 전입니다.")

    config = {"configurable": {"thread_id": f"{req.user_id}_{req.session_id}"}}
    initial_state = {
        "messages": [HumanMessage(content=req.message)],
        "user_id": req.user_id,
        "session_id": req.session_id,
        "permissions": {"allow_vision": False},
        "sensory_data": {}
    }

    try:
        final_state = await graph.ainvoke(initial_state, config=config)
        return {
            "status": "success", 
            "response": final_state["messages"][-1].content
        }
    except Exception as e:
        logger.error(f"채팅 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 8080 포트로 실행
    uvicorn.run("supporter_ai.main:app", host="0.0.0.0", port=8080, reload=True)