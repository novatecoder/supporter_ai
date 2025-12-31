
# [SDS] 서포터 AI (Supporter AI) 상세 설계서

## 1. 시스템 아키텍처 (Hybrid Orchestrator Brain)

본 시스템은 감정(Emotion)과 이성(Reason)이 상호작용하는 **하이브리드 오케스트레이터** 구조를 채택합니다. 사용자가 기능을 제어할 수 있으며, AI는 자신의 가용 능력을 인지하고 이에 맞춰 대화(티키타카)를 진행합니다.

### 1.1 노드 유형 정의

1. **Code Node**: 데이터 로드/저장, 외부 API 호출 등 정해진 로직을 수행하는 순수 파이썬 노드.
2. **Logic Node (Base Model)**: 의도 분석, 추론, 정보 인지 후 감정 수치 계산을 담당하는 논리 노드.
3. **LoRA Node (Persona Model)**: 결정된 상태를 바탕으로 혈액형별 말투와 페르소나를 입히는 표현 노드.

## 2. 인지-감정 워크플로우 (Cognitive-Emotional Loop)

AI는 정보를 습득함에 따라 실시간으로 기분이 변화하며, 이는 다음 대화에 즉각 반영됩니다.

1. **Sensory Analyzer**: 사용자의 입력(텍스트/파일)과 의도를 분석합니다.
2. **Brain Orchestrator**: 이성적으로 판단하여 도구(검색 등) 사용 여부를 결정합니다. 기능이 꺼져 있을 경우 이를 인지하고 사용자에게 요청합니다.
3. **Tool Execution & Gateway**: 실제로 도구를 실행합니다. 사용자가 비활성화한 도구는 시스템 레벨에서 차단됩니다.
4. **Dynamic Emotion Update**: 도구 실행 결과(예: 검색된 정보의 내용)를 보고 "기쁨", "놀람" 등의 감정 수치를 업데이트합니다.
5. **Expression Node (LoRA Apply)**: 혈액형 플래그(A, B, O, AB)에 따라 LoRA 어댑터를 적용하여 최종 페르소나 답변을 생성합니다.

## 3. 계층형 메모리 시스템 (Memory Layer)

* **Redis (Short-term)**: 최근 대화 맥락 및 요약본 저장.
* **PostgreSQL (Persona)**: 혈액형 및 사용자 환경 설정 저장.
* **Neo4j (Knowledge Graph)**: 사용자 주변 인물 및 사실 관계 저장.
* **Vector DB (Episodic)**: 과거의 중요한 사건 및 경험 저장.

## 4. 데이터 인터페이스 규격 (API JSON)

### 4.1 Input Packet (확장형)

```json
{
  "user_id": "kwh_01",
  "input_text": "이 케이크 뭐야? 진짜 이쁘다!",
  "input_files": [],
  "enabled_tools": ["stt", "tts", "google_search"]
}

```

### 4.2 Output Packet (구조화된 출력)

```json
{
  "response": {
    "text": "우와, 진짜네! 검색해 보니까 이건 딸기 생크림 케이크래. 너무 맛있어 보여서 나도 기분이 좋아졌어!",
    "emotion": {
      "type": "happy",
      "intensity": 0.9,
      "visual_hint": "heart_eyes"
    },
    "action": {
      "command": "none",
      "params": {}
    }
  },
  "metadata": {
    "blood_type": "A",
    "thought_process": "사용자가 케이크를 언급함 -> 검색 결과 확인 -> 긍정적 정보 인지 -> 기쁨 수치 상승"
  }
}

```

## 5. 자가 피드백 (Background Reflection)

답변이 사용자에게 전달된 후, 백그라운드 노드에서 방금의 발화가 설정된 혈액형 페르소나와 감정 상태에 적절했는지 스스로 평가하여 메모리에 피드백을 기록합니다.