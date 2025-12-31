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

# 앱 상태 공유
app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 랭그래프 엔진 로딩"""
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

async def run_post_processing(graph, state: Dict[str, Any]):
    """
    요약(Summarize), 저장(Save), 성찰(Reflection) 등 무거운 작업을 
    사용자에게 응답을 보낸 뒤 백그라운드에서 처리하기 위한 함수입니다.
    현재 workflow 구조상 ainvoke 내부에서 순차적으로 실행되지만, 
    로그를 통해 실행 여부를 모니터링합니다.
    """
    try:
        # 요약 노드가 실행되었는지 로그 확인
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

    # 그래프 시작 상태 설정
    initial_state = {
        "input_text": req.message,
        "user_id": req.user_id,
        "session_id": req.session_id,
        "blood_type": req.blood_type,
        "enabled_tools": req.enabled_tools,
        "disabled_tools": req.disabled_tools,
        "messages": [] # load_memory_node에서 Redis 데이터로 채워짐
    }

    try:
        # 1. 랭그래프 실행
        # [참고] 현재 workflow 구조상 save_memory까지 일직선으로 실행됩니다.
        # recursion_limit을 50으로 늘려 루프 에러를 방지합니다.
        final_state = await graph.ainvoke(
            initial_state, 
            config={"recursion_limit": 50}
        )
        
        # 2. 결과 추출
        ai_response = final_state.get("final_output")
        
        # 방어적 코드: 응답이 없는 경우
        if not ai_response or not isinstance(ai_response, dict):
            ai_response = {
                "text": "미안해, 대답을 준비하는 중에 문제가 생겼어. 다시 말해줄래?",
                "emotion": "sad",
                "action": "none"
            }

        # 3. 백그라운드 작업 등록
        # 요약 및 성찰 결과가 포함된 상태를 백그라운드 로그에 남깁니다.
        background_tasks.add_task(run_post_processing, graph, final_state)

        # 4. 클라이언트 디버깅용 메타데이터 구성
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
            "response": ai_response,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"❌ 채팅 실행 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("supporter_ai.main:app", host="0.0.0.0", port=settings.APP_PORT, reload=settings.DEBUG)