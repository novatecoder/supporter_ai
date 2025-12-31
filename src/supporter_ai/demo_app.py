import streamlit as st
import requests
import asyncio
import threading
import numpy as np
from supporter_ai.sensory.whisper_engine import WhisperEngine
from supporter_ai.expression.tts_engine import TTSEngine

# --- [1. 페이지 및 스타일 설정] ---
st.set_page_config(page_title="Supporter AI Debug Console", layout="wide")

# 카카오톡 스타일 테마 적용
st.markdown("""
    <style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* 사용자 메시지: 노란색 우측 정렬 */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) {
        background-color: #FEE500 !important;
        color: #000000 !important;
        margin-left: auto;
        width: fit-content;
        max-width: 75%;
    }
    /* AI 메시지: 흰색 좌측 정렬 */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #DDDDDD;
        margin-right: auto;
        width: fit-content;
        max-width: 75%;
    }
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [2. 엔진 및 세션 상태 초기화] ---
@st.cache_resource
def get_engines():
    """STT 및 TTS 엔진 로드"""
    return WhisperEngine(), TTSEngine()

stt_engine, tts_engine = get_engines()

# 세션 상태 초기화 (AttributeError 방지를 위해 st.session_state 사용)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "blood_type" not in st.session_state:
    st.session_state.blood_type = "A"
if "user_id" not in st.session_state:
    st.session_state.user_id = "kwh_01"
if "session_id" not in st.session_state:
    st.session_state.session_id = "sess_01"

# --- [3. 사이드바: 유저/세션 및 기능 제어] ---
with st.sidebar:
    st.header("👤 사용자 및 세션 제어")
    # 유저 ID 및 세션 ID 실시간 수정
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)
    st.session_state.session_id = st.text_input("Session ID", value=st.session_state.session_id)
    
    # 혈액형 페르소나 선택
    blood_types = ["A", "B", "O", "AB"]
    st.session_state.blood_type = st.selectbox(
        "혈액형 페르소나 설정", 
        blood_types, 
        index=blood_types.index(st.session_state.blood_type)
    )
    
    st.markdown("---")
    st.header("🛠️ 기능 제어")
    search_on = st.toggle("구글 검색 활성화", value=True)
    enabled_tools = ["google_search"] if search_on else []
    
    if st.button("🗑️ 대화 초기화"):
        st.session_state.chat_history = []
        st.rerun()

# --- [4. 서버 통신 로직] ---
def send_to_server(message):
    """FastAPI 서버에 메시지 전송 및 응답 처리"""
    if not message:
        return

    # [수정 포인트] st.session_id -> st.session_state.session_id 로 변경됨
    payload = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.session_id, 
        "message": message,
        "blood_type": st.session_state.blood_type,
        "enabled_tools": enabled_tools
    }
    
    try:
        # main.py의 chat 엔드포인트 호출
        response = requests.post("http://localhost:8080/api/v1/chat", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            res_body = data["response"]
            
            # 히스토리에 사용자 및 AI 메시지 추가
            st.session_state.chat_history.append({"role": "user", "content": message})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": res_body.get("text", ""),
                "emotion": res_body.get("emotion", {}),
                "debug_info": data.get("metadata", {})
            })
        else:
            st.error(f"서버 오류: {response.status_code}")
    except Exception as e:
        st.error(f"서버 연결 실패: {str(e)}")

# --- [5. 채팅 출력 영역] ---
st.title(f"🤖 Supporter AI ({st.session_state.blood_type}형 모드)")

chat_container = st.container(height=550)
with chat_container:
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])
            
            if chat["role"] == "assistant":
                # 음성 재생 버튼과 디버그 정보 배치
                col_tts, col_debug = st.columns([1, 5])
                with col_tts:
                    if st.button("🔊 재생", key=f"tts_{i}"):
                        with st.spinner("말하는 중..."):
                            # TTS 엔진을 통한 음성 출력
                            asyncio.run(tts_engine.speak(chat["content"]))
                
                with col_debug:
                    with st.expander("사고 과정 보기"):
                        st.json(chat.get("debug_info", {}))

# --- [6. 하단 입력 및 녹음 영역] ---
st.markdown("---")
input_col1, input_col2 = st.columns([1, 6])

with input_col1:
    # 녹음 상태 토글 버튼
    if not st.session_state.is_recording:
        if st.button("🎙️ 녹음 시작", use_container_width=True):
            st.session_state.is_recording = True
            st.rerun()
    else:
        if st.button("🛑 전송하기", type="primary", use_container_width=True):
            st.session_state.is_recording = False
            # 실제 구현 시 여기에 Whisper STT 로직 연결
            st.toast("음성 인식 중...") 
            st.rerun()

with input_col2:
    # 텍스트 입력창 (하단 고정)
    if prompt := st.chat_input("메시지를 입력하세요..."):
        send_to_server(prompt)
        st.rerun()