import streamlit as st
import requests
import numpy as np
import pyaudio
import threading
import asyncio
from supporter_ai.sensory.whisper_engine import WhisperEngine
from supporter_ai.expression.tts_engine import TTSEngine

# 페이지 설정
st.set_page_config(page_title="Supporter AI Debug Console", layout="wide")

# --- [엔진 및 상태 초기화] ---
@st.cache_resource
def get_engines():
    return WhisperEngine(), TTSEngine()

stt_engine, tts_engine = get_engines()

# 세션 상태 초기화 (지속성 유지)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "audio_buffer" not in st.session_state:
    st.session_state.audio_buffer = []
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()

# 페르소나 및 도구 설정 세션 유지
if "blood_type" not in st.session_state:
    st.session_state.blood_type = "A"
if "enabled_tools" not in st.session_state:
    st.session_state.enabled_tools = ["google_search"]

# --- [UI 구성] ---
st.title("🤖 Supporter AI 데모 (Hybrid Brain)")

# 사이드바 설정 (설정 지속성 구현)
with st.sidebar:
    st.header("👤 세션 설정")
    user_id = st.text_input("User ID", value="kwh_01")
    session_id = st.text_input("Session ID", value="sess_01")
    
    # 혈액형 페르소나 선택
    st.session_state.blood_type = st.selectbox(
        "혈액형 페르소나", ["A", "B", "O", "AB"], 
        index=["A", "B", "O", "AB"].index(st.session_state.blood_type)
    )
    
    st.markdown("---")
    st.header("🛠️ 기능 제어")
    # 도구 활성화 플래그 제어
    search_on = st.toggle("구글 검색 활성화", value="google_search" in st.session_state.enabled_tools)
    
    enabled_tools = []
    disabled_tools = []
    if search_on:
        enabled_tools = ["google_search"]
        st.session_state.enabled_tools = enabled_tools
    else:
        enabled_tools = []
        disabled_tools = ["google_search"]
        st.session_state.enabled_tools = enabled_tools

    if st.button("🗑️ 대화 초기화"):
        st.session_state.chat_history = []
        st.rerun()

# --- [서버 통신 로직] ---
def send_to_server(user_id, session_id, message):
    try:
        # 매번 현재 세션 설정(혈액형, 도구 상태)을 함께 전송
        payload = {
            "user_id": user_id, 
            "session_id": session_id, 
            "message": message,
            "blood_type": st.session_state.blood_type,
            "enabled_tools": st.session_state.enabled_tools,
            "disabled_tools": disabled_tools
        }
        
        response = requests.post("http://localhost:8080/api/v1/chat", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            res_body = data["response"] # 구조화된 응답 JSON
            
            content = res_body.get("text", "")
            emotion = res_body.get("emotion", {})
            
            st.session_state.chat_history.append({"role": "user", "content": message})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": content,
                "emotion": emotion,
                "debug_info": data.get("metadata", {})
            })
    except Exception as e:
        st.error(f"서버 연결 실패: {str(e)}")

# --- [채팅 출력 및 입력 영역] ---
chat_container = st.container(height=600)
with chat_container:
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])
            if chat["role"] == "assistant":
                col_tts, col_debug = st.columns([1, 4])
                with col_tts:
                    if st.button("🔊 재생", key=f"tts_{i}"):
                        asyncio.run(tts_engine.speak(chat["content"]))
                
                if "debug_info" in chat:
                    with st.expander("🛠️ 상세 사고 과정 및 데이터"):
                        st.json(chat["debug_info"])

st.markdown("---")
input_col1, input_col2 = st.columns([1, 5])

# 오디오 및 텍스트 입력 로직 (기존과 동일)
with input_col1:
    if not st.session_state.is_recording:
        if st.button("🎙️ 녹음", use_container_width=True):
            st.session_state.is_recording = True
            st.session_state.stop_event.clear()
            st.session_state.audio_buffer = []
            # ... (recording thread logic)
            st.rerun()
    else:
        if st.button("🛑 전송", type="primary", use_container_width=True):
            st.session_state.stop_event.set()
            st.session_state.is_recording = False
            # ... (stt & send logic)
            st.rerun()

with input_col2:
    if prompt := st.chat_input("메시지를 입력하세요..."):
        send_to_server(user_id, session_id, prompt)
        st.rerun()