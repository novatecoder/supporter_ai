# src/supporter_ai/common/db_utils.py
import logging
import uuid
from typing import List
from sqlalchemy import Column, String, Float, DateTime, Text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from qdrant_client import AsyncQdrantClient, models # 패키지 임포트
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)
Base = declarative_base()

class MemoryMetadata(Base):
    __tablename__ = "memory_metadata"
    id = Column(String, primary_key=True) 
    user_id = Column(String, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# 비동기 Postgres 엔진 (asyncpg 필수)
engine = create_async_engine(settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://"))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Qdrant 1.16.2 비동기 클라이언트 초기화
# 변수명을 패키지명(qdrant_client)과 다르게 설정하여 충돌 방지
qdrant_async_engine = AsyncQdrantClient(
    host=settings.QDRANT_HOST, 
    port=settings.QDRANT_PORT
)
COLLECTION_NAME = "supporter_memories"

async def init_db():
    """Postgres 테이블 및 Qdrant 컬렉션 초기화"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        if not await qdrant_async_engine.collection_exists(COLLECTION_NAME):
            await qdrant_async_engine.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
            )
        logger.info("✅ PostgreSQL & Qdrant (1.16.2) 비동기 시스템 준비 완료.")
    except Exception as e:
        logger.error(f"❌ DB 초기화 중 치명적 에러: {e}")

async def save_memory_to_db(user_id: str, content: str, vector: List[float], importance: float):
    """장기 기억 통합 저장 (Qdrant + Postgres)"""
    memory_id = str(uuid.uuid4())
    
    # Qdrant 1.16.2 upsert
    await qdrant_async_engine.upsert(
        collection_name=COLLECTION_NAME,
        points=[models.PointStruct(id=memory_id, vector=vector, payload={"user_id": user_id})]
    )
    
    # Postgres 메타데이터 저장
    async with AsyncSessionLocal() as session:
        async with session.begin():
            new_meta = MemoryMetadata(id=memory_id, user_id=user_id, content=content, importance=importance)
            session.add(new_meta)
        await session.commit()

async def search_memory_db(user_id: str, query_vector: List[float], limit: int = 3) -> str:
    """Qdrant 1.16.2의 query_points API를 사용한 고속 검색"""
    try:
        # search 메서드 대신 1.16.2에서 권장하는 query_points 사용
        results = await qdrant_async_engine.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))]
            ),
            limit=limit
        )
        
        if not results or not results.points:
            return "관련된 과거 기억 없음"
        
        # 검색된 ID 리스트 추출
        ids = [str(res.id) for res in results.points]
        
        async with AsyncSessionLocal() as session:
            stmt = select(MemoryMetadata.content).where(MemoryMetadata.id.in_(ids))
            res = await session.execute(stmt)
            contents = res.scalars().all()
            return "\n- ".join(contents) if contents else "관련된 과거 기억 없음"
            
    except Exception as e:
        logger.error(f"❌ 장기 기억 검색 중 에러 발생: {e}")
        # 만약 query_points마저 실패할 경우를 대비한 최후의 보루 (기본 문구 반환)
        return "과거에 우리가 나눈 대화를 찾아보려 했는데 잘 안 됐어. 미안!"