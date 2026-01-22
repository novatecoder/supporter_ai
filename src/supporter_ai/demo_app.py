# src/supporter_ai/demo_app.py
import streamlit as st
import requests
import asyncio
import json
import numpy as np
from supporter_ai.sensory.whisper_engine import WhisperEngine
from supporter_ai.expression.tts_engine import TTSEngine

# --- [1. 페이지 설정] ---
st.set_page_config(page_title="Supporter AI Console", layout="wide")

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

# --- [2. 상태 초기화] ---
@st.cache_resource
def get_engines():
    return WhisperEngine(), TTSEngine()

stt_engine, tts_engine = get_engines()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "current_ai_pad" not in st.session_state:
    st.session_state.current_ai_pad = {"p": 0.0, "a": 0.0, "d": 0.0}
if "blood_type" not in st.session_state:
    st.session_state.blood_type = "A"

# --- [3. 사이드바: PAD 대시보드] ---
with st.sidebar:
    st.title("🧠 AI State (PAD)")
    pad = st.session_state.current_ai_pad
    
    def get_progress_val(val):
        return float(np.clip((val + 1) / 2, 0.0, 1.0))

    st.subheader("Pleasure")
    st.progress(get_progress_val(pad["p"]))
    st.caption(f"P: {pad['p']:.2f}")
    
    st.subheader("Arousal")
    st.progress(get_progress_val(pad["a"]))
    st.caption(f"A: {pad['a']:.2f}")
    
    st.subheader("Dominance")
    st.progress(get_progress_val(pad["d"]))
    st.caption(f"D: {pad['d']:.2f}")
    
    st.markdown("---")
    st.session_state.blood_type = st.selectbox("페르소나", ["A", "B", "O", "AB"])
    
    if st.button("🗑️ 초기화"):
        st.session_state.chat_history = []
        st.session_state.current_ai_pad = {"p": 0.0, "a": 0.0, "d": 0.0}
        st.rerun()

# --- [4. 통신 로직] ---
def send_to_server(message):
    if not message: return

    # [수정] 내 말을 즉시 히스토리에 추가하여 화면에 먼저 보이게 함
    st.session_state.chat_history.append({"role": "user", "content": message})
    
    payload = {
        "user_id": "kwh_01",
        "session_id": "sess_01", 
        "message": message,
        "blood_type": st.session_state.blood_type,
        "history": st.session_state.chat_history[:-1] # 이전 기록들만 보냄
    }
    
    try:
        # 응답 대기 시각화
        with st.spinner("생각 중..."):
            response = requests.post("http://localhost:8080/api/v1/chat", json=payload, timeout=90)
        
        if response.status_code == 200:
            data = response.json()
            res_body = data["response"]
            metadata = data.get("metadata", {})
            
            # AI 답변 추가
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": res_body.get("text", ""),
                "emotion": res_body.get("emotion", "neutral"),
                "action": res_body.get("action", "none"),
                "debug_info": metadata
            })
            # PAD 상태 즉시 반영
            if "ai_pad" in metadata:
                st.session_state.current_ai_pad = metadata["ai_pad"]
        else:
            st.error("서버 응답 실패")
    except Exception as e:
        st.error(f"연결 에러: {e}")

# --- [5. 채팅창] ---
st.title(f"🤖 Supporter AI ({st.session_state.blood_type}형)")

container = st.container(height=500)
with container:
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])
            if chat["role"] == "assistant":
                st.caption(f"🎭 {chat.get('emotion')} | 🎬 {chat.get('action')}")
                if st.button("🔊 재생", key=f"tts_{i}"):
                    asyncio.run(tts_engine.speak(chat["content"]))
                with st.expander("생각 보기"):
                    st.json(chat.get("debug_info", {}))

# --- [6. 입력창] ---
if prompt := st.chat_input("할 말을 입력해줘"):
    send_to_server(prompt)
    st.rerun()