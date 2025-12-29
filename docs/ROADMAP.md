# 🚀 서포터 AI (Supporter AI) 개발 로드맵

## [Phase 1: Zero to Chat (기반 구축)] - ✅ 완료
* **1단계: 프로젝트 스캐폴딩 및 기본 채팅**
    * LangGraph 런타임 및 vLLM 연동 완료.
* **2단계: 메모리 최적화 및 요약 로직**
    * Redis 연동 및 2048 토큰 대응 Summarize Node 구현 완료.

---

## [Phase 2: 앱 기반 감각과 표현 (App Sensory & Expression)] - 🔄 진행 중
* **3단계: 클라이언트 측 STT (OpenAI Whisper) 통합**
    * 앱(데모)에서 마이크 입력을 처리하고 텍스트를 서버로 전송하는 기능 구현.
* **4단계: 클라이언트 측 TTS (Edge-TTS) 통합**
    * 서버의 응답 JSON을 받아 앱에서 성격에 맞는 목소리로 출력하는 기능 구현.

---

## [Phase 3: 뇌 기능 강화 (Brain Power-up)] - 📅 예정
* **5단계: 추론 프로세스 고도화**
    * 단순 답변을 넘어 Chain of Thought(CoT) 및 자가 성찰(Reflection) 강화.
* **6단계: 외부 지식 습득 (Google Search Tool)**
    * 필요 시 스스로 검색하여 답변에 반영하는 도구 사용 능력 추가.

---

## [Phase 4: 혈액형 페르소나와 감정 (Persona & Emotion)] - 📅 예정
* **7단계: 혈액형 기반 LoRA 연동 설계**
    * A, B, O, AB형별 성격 데이터 정의 및 외부 학습 LoRA 어댑터 전환 로직 구현.
* **8단계: 다차원 인격 수치화 (Big5/PAC)**
    * PostgreSQL 기반 복합 인격 시스템과 대화 로직 연결.

---

## [Phase 5: 관계와 시각의 확장 (Growth & Vision)] - 📅 예정
* **9단계: Neo4j 관계형 지식 구축**
    * 사용자 선호도 및 관계를 그래프로 저장하고 성장에 반영.
* **10단계: Vision 노드를 통한 화면 인지**
    * VLM을 활용해 게임 화면(TFT 등) 상황을 실시간 인지하고 대화에 반영.

---

## [Phase 6: 완성 및 배포 (Packaging)]
* **11단계: 리소스 최적화 및 하이브리드 모드**
* **12단계: 실행 파일(.exe) 제작 및 독립 배포**