# 🤖 Supporter AI (서포터 AI)

> **로컬 LLM 기반 지능형 서포터 에이전트**
> 사용자의 감정을 이해하고, 음성과 시각을 통해 소통하며 업무를 돕는 하이브리드 AI 에이전트입니다. 감정(Emotion)과 이성(Reason)이 상호작용하는 **하이브리드 오케스트레이터** 구조를 통해 고도화된 페르소나 대화 경험을 제공합니다.

---

## ✨ 주요 기능 (Key Features)

* **인지-감정 루프 (Cognitive-Emotional Loop):** 실시간 정보 습득 및 도구 실행 결과에 따라 AI의 감정 수치가 변화하며 대화에 반영됩니다.
* **혈액형 페르소나 시스템:** A, B, O, AB형 플래그에 따라 차별화된 말투와 페르소나를 입히는 표현 노드를 탑재하고 있습니다.
* **멀티모달 인터랙션:** 음성 인식(Whisper), 음성 합성(Edge-TTS), 시각 정보 분석(Vision)을 통합한 다각적 소통이 가능합니다.
* **계층형 메모리 구조:** Redis, PostgreSQL, Neo4j, Qdrant를 결합하여 단기/장기/관계형 기억을 체계적으로 관리합니다.

---

## 🏗 시스템 아키텍처 (Architecture)

본 시스템은 세 가지 핵심 노드 유형을 통해 복합적인 추론 프로세스를 수행합니다:

1. **Code Node**: 데이터 로드/저장 및 외부 API 호출 등 정적인 로직 수행.
2. **Logic Node**: 의도 분석 및 감정 수치를 계산하는 이성적 판단 영역.
3. **LoRA Node**: 결정된 상태를 바탕으로 혈액형별 페르소나를 적용하여 답변을 생성하는 표현 영역.

---

## 🛠 기술 스택 (Tech Stack)

### AI & Framework

* **Orchestration:** LangGraph (Stateful Workflow)
* **LLM Engine:** vLLM (Qwen2.5-7B-Instruct-AWQ)
* **STT/TTS:** OpenAI Whisper, Edge-TTS

### Database (Infra)

* **Memory (Short-term):** Redis Stack (RedisInsight 포함)
* **Persona & Meta:** PostgreSQL
* **Knowledge Graph:** Neo4j (인물 및 사실 관계)
* **Vector DB:** Qdrant (에피소드 기억)

---

## 🚀 시작하기 (Getting Started)

### 1. 필수 의존성 설치

시스템의 오디오 처리 및 멀티미디어 기능을 위해 아래 패키지 설치가 필요합니다.

```bash
sudo apt install ffmpeg
sudo apt-get install portaudio19-dev python3-all-dev

```

### 2. 라이브러리 설치 (Poetry)

```bash
poetry install

```

### 3. 인프라 서비스 실행 (Docker Compose)

데이터베이스 및 AI 엔진을 컨테이너 환경에서 구동합니다.

```bash
docker-compose up -d

```

---

## 💻 실행 방법 (Execution)

### 1. 백엔드 API 서버 실행

FastAPI 기반의 하이브리드 엔진을 로드합니다.

```bash
poetry run python -m supporter_ai.main

```

### 2. 디버그 콘솔(UI) 실행

사용자 인터페이스 및 음성 제어를 위한 Streamlit 앱을 구동합니다.

```bash
streamlit run src/supporter_ai/demo_app.py

```

---

## 🔍 서비스 상태 체크 (Service Health)

시스템 구동 후 아래 주소들을 통해 각 서비스의 정상 작동 여부를 확인할 수 있습니다:

| 서비스명 | 포트 | 용도 | 확인 방법 |
| --- | --- | --- | --- |
| **API Server** | `8080` | 메인 채팅 인터페이스 | `http://localhost:8080/docs` 접속 (Swagger) |
| **vLLM Engine** | `8000` | LLM 추론 서버 | `http://localhost:8000/v1/models` API 응답 확인 |
| **RedisInsight** | `8001` | 메모리/로그 모니터링 | `http://localhost:8001` 웹 대시보드 접속 |
| **Neo4j** | `7474` | 지식 그래프 관리 | `http://localhost:7474` (ID/PW: neo4j/password) |
| **Qdrant** | `6333` | 벡터 데이터 확인 | `http://localhost:6333/dashboard` 접속 |

---

## 🗺 로드맵 (Roadmap)

상세한 개발 진행 상황 및 향후 계획은 [ROADMAP.md](https://www.google.com/search?q=./docs/ROADMAP.md)에서 확인하실 수 있습니다.

---
