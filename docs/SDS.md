# [SDS] 서포터 AI (Supporter AI) 상세 설계서

## 1. 시스템 아키텍처 (Headless Brain & Sensory App)

본 시스템은 감정(Emotion)과 이성(Reason)이 분리된 복합 뇌 구조를 서버에 두고, 사용자와의 실시간 소통을 담당하는 감각(Sensory) 및 표현(Expression) 기능을 클라이언트(앱)로 분리한 구조를 지향합니다. 모든 통신은 표준화된 JSON을 통해 이루어집니다.

### 1.1 상태 관리 및 분석 흐름
* **JSON Interface**: 클라이언트가 STT를 통해 텍스트화된 입력과 센서 데이터를 JSON으로 전송하면, 서버는 이를 처리하여 답변과 상태 정보를 JSON으로 반환합니다.
* **Decoupled Logic**: 입력이 들어오면 **감정 노드**가 먼저 반응하여 AI의 내부 상태를 변화시키고, **뇌 노드**가 그 상태를 바탕으로 말투와 내용을 결정합니다.
* **Hybrid Memory**: Redis(단기/감정), PostgreSQL(인격/성장), Neo4j(관계), Vector DB(경험)를 단계적으로 결합합니다.

## 2. 데이터베이스 및 심리 모델 설계

### 2.1 4단계 레이어 메모리 (Redis + SQL + Graph + Vector)
1. **Redis (Short-term)**: 현재 대화의 기분(Mood), '킹받음' 지수, 최근 대화 맥락.
2. **PostgreSQL (Persona)**:
    * **Big5**: 외향성, 친화성 등 기본 성격 수치.
    * **교류분석(TA)**: 부모(P), 성인(A), 아이(C) 자아 상태 수치.
    * **다크 트라이어드**: 자기주장 및 독설 수위 조절용.
3. **Neo4j (Knowledge Graph)**: 사용자 주변 인물, 선호도, 싫어하는 것(장난 소재).
4. **Vector DB (Episodic)**: 과거의 중요한 사건 및 학습된 지식.

## 3. 멀티 에이전트 노드 구성 (LangGraph & App)

| 위치 | 노드/기능 | 역할 및 세부 로직 |
| --- | --- | --- |
| **App** | **Sensory (STT)** | 마이크 입력 -> Whisper 엔진 -> 텍스트 JSON 전송. |
| **Server** | **Input Node** | 클라이언트 JSON 수신 및 데이터 필터링. |
| **Server** | **Emotional Node** | 실시간 기분 수치 업데이트 및 LoRA 어댑터 결정. |
| **Server** | **Brain Node** | **(강화 대상)** 결정된 감정과 혈액형 성격 수치를 조합해 답변 생성. |
| **Server** | **Summarize Node** | 2048 토큰 제한 준수를 위한 기억 압축 및 요약. |
| **Server** | **Sensory Tools** | 구글 검색, 시스템 모니터링, 비전 분석 기능. |
| **Server** | **Reflection Node** | 사용자 반응 분석 및 인격 수치 미세 조정. |
| **App** | **Expression (TTS)** | 서버 응답 JSON 수신 -> Edge-TTS 엔진 -> 음성 출력. |