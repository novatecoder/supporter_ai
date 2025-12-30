### 1. ROADMAP.md 업데이트

# 🚀 서포터 AI (Supporter AI) 개발 로드맵

## [Phase 1: Zero to Chat (기반 구축)] - ✅ 완료

* **1단계: 프로젝트 스캐폴딩 및 기본 채팅**
* LangGraph 런타임 및 vLLM 연동 완료.


* **2단계: 메모리 최적화 및 요약 로직**
* Redis 연동 및 2048 토큰 대응 `summarize_node` 구현 완료.



## [Phase 2: 앱 기반 감각과 표현 (App Sensory & Expression)] - ✅ 완료

* **3단계: 클라이언트 측 STT (OpenAI Whisper) 통합**
* 마이크 입력 처리 및 텍스트화 엔진 구현 완료.


* **4단계: 클라이언트 측 TTS (Edge-TTS) 통합**
* 응답 텍스트의 음성 변환 및 재생 기능 구현 완료.



## [Phase 3: 지능형 하이브리드 뇌 (Hybrid Orchestrator)] - 🔄 진행 중

* **5단계: 모듈형 노드 구조 전환**
* 순수 코드(Code), 논리(Logic), 페르소나(LoRA) 노드로 역할 분리.
* 동적 도구 활성화/비활성화 게이트웨이 구축 (AI의 기능 상태 인지).


* **6단계: 인지-감정 업데이트 루프 (Iterative Reasoning)**
* 검색 및 도구 실행 결과를 바탕으로 실시간 감정이 변화하는 로직 구현.
* 확장 가능한 JSON 규격의 멀티모달 출력(텍스트+감정+행동) 설계.



## [Phase 4: 지식과 관계의 확장 (Knowledge & Relationship)] - 📅 예정

* **7단계: 계층형 메모리 시스템 통합**
* Neo4j(인물 관계), PostgreSQL(영구 설정), Vector DB(과거 경험) 연동.


* **8단계: 자가 성찰(Reflection) 모듈**
* 답변 후 백그라운드에서 페르소나 적합성을 평가하고 피드백을 저장하는 기능.



## [Phase 5: 완성 및 독립 배포 (Packaging)] - 📅 예정

* **9단계: 비전(Vision) 및 시스템 제어 확장**
* 시각 정보 분석 및 마우스/키보드 제어 도구 추가.


* **10단계: 실행 파일(.exe) 제작 및 최적화**.
