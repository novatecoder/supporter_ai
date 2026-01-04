import streamlit as st
import requests
import asyncio
import json
import numpy as np  # 수치 제한(Clip)을 위해 추가
from supporter_ai.sensory.whisper_engine import WhisperEngine
from supporter_ai.expression.tts_engine import TTSEngine

# --- [1. 페이지 및 스타일 설정] ---
st.set_page_config(page_title="Supporter AI PAD Console", layout="wide")

# 카카오톡 스타일 테마 적용
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageUser"]) {
        background-color: #FEE500 !important; color: #000000 !important;
        margin-left: auto; width: fit-content; max-width: 75%;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAssistant"]) {
        background-color: #FFFFFF !important; border: 1px solid #DDDDDD;
        margin-right: auto; width: fit-content; max-width: 75%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [2. 엔진 및 세션 상태 초기화] ---
@st.cache_resource
def get_engines():
    """STT 및 TTS 엔진 로드"""
    return WhisperEngine(), TTSEngine()

stt_engine, tts_engine = get_engines()

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
# AI의 현재 PAD 상태 저장
if "current_ai_pad" not in st.session_state:
    st.session_state.current_ai_pad = {"p": 0.0, "a": 0.0, "d": 0.0}

# --- [3. 사이드바: PAD 대시보드 및 설정] ---
with st.sidebar:
    st.title("🧠 AI 내부 상태 (PAD)")
    
    pad = st.session_state.current_ai_pad
    
    # [수정] -1~1 수치를 0~1 범위로 안전하게 변환하는 헬퍼 함수
    def get_progress_val(val):
        # (val + 1) / 2를 통해 -1은 0으로, 1은 1로 변환하고 np.clip으로 범위를 강제함
        return float(np.clip((val + 1) / 2, 0.0, 1.0))

    st.subheader("Pleasure (쾌락)")
    st.progress(get_progress_val(pad["p"]))
    st.caption(f"수치: {pad['p']:.2f} (음수: 불만/슬픔, 양수: 만족/기쁨)")
    
    st.subheader("Arousal (각성)")
    st.progress(get_progress_val(pad["a"]))
    st.caption(f"수치: {pad['a']:.2f} (음수: 침착/무기력, 양수: 흥분/분노)")
    
    st.subheader("Dominance (지배)")
    st.progress(get_progress_val(pad["d"]))
    st.caption(f"수치: {pad['d']:.2f} (음수: 위축/순응, 양수: 주도/자신감)")
    
    st.markdown("---")
    st.header("👤 세션 설정")
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)
    st.session_state.session_id = st.text_input("Session ID", value=st.session_state.session_id)
    
    blood_types = ["A", "B", "O", "AB"]
    st.session_state.blood_type = st.selectbox(
        "혈액형 페르소나 설정", 
        blood_types, 
        index=blood_types.index(st.session_state.blood_type)
    )
    
    st.markdown("---")
    search_on = st.toggle("구글 검색 활성화", value=False)
    enabled_tools = ["google_search"] if search_on else []
    
    if st.button("🗑️ 대화 초기화"):
        st.session_state.chat_history = []
        st.session_state.current_ai_pad = {"p": 0.0, "a": 0.0, "d": 0.0}
        st.rerun()

# --- [4. 서버 통신 로직] ---
def send_to_server(message):
    """FastAPI 서버에 메시지 전송 및 응답 처리"""
    if not message: return

    payload = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.session_id, 
        "message": message,
        "blood_type": st.session_state.blood_type,
        "enabled_tools": enabled_tools
    }
    
    try:
        response = requests.post("http://localhost:8080/api/v1/chat", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            res_body = data["response"]
            metadata = data.get("metadata", {})
            
            # [추가] 서버에서 받은 최신 AI PAD 상태 업데이트
            if "ai_pad" in metadata:
                st.session_state.current_ai_pad = metadata["ai_pad"]
            
            st.session_state.chat_history.append({"role": "user", "content": message})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": res_body.get("text", ""),
                "emotion": res_body.get("emotion", "normal"),
                "action": res_body.get("action", "none"),
                "debug_info": metadata
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
                # 감정 및 행동 태그 출력
                st.caption(f"🎭 표정: {chat.get('emotion')} | 🎬 행동: {chat.get('action')}")
                
                col_tts, col_debug = st.columns([1, 5])
                with col_tts:
                    if st.button("🔊 재생", key=f"tts_{i}"):
                        with st.spinner("생성 중..."):
                            asyncio.run(tts_engine.speak(chat["content"]))
                
                with col_debug:
                    with st.expander("사고 과정 및 기억 데이터 보기"):
                        st.json(chat.get("debug_info", {}))

# --- [6. 하단 입력 및 녹음 영역] ---
st.markdown("---")
input_col1, input_col2 = st.columns([1, 6])

with input_col1:
    if not st.session_state.is_recording:
        if st.button("🎙️ 녹음 시작", use_container_width=True):
            st.session_state.is_recording = True
            st.rerun()
    else:
        if st.button("🛑 전송하기", type="primary", use_container_width=True):
            st.session_state.is_recording = False
            st.rerun()

with input_col2:
    if prompt := st.chat_input("메시지를 입력하세요..."):
        send_to_server(prompt)
        st.rerun()