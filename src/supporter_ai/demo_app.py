import streamlit as st
import requests
import json
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
    """엔진들을 캐싱하여 중복 로드를 방지합니다."""
    return WhisperEngine(), TTSEngine()

stt_engine, tts_engine = get_engines()

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "audio_buffer" not in st.session_state:
    st.session_state.audio_buffer = []
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()

# --- [오디오 및 서버 통신 로직] ---

def audio_recording_worker(stop_event, buffer):
    """백그라운드 스레드에서 실제 마이크 소리를 캡처합니다."""
    CHUNK, FORMAT, CHANNELS, RATE = 1024, pyaudio.paInt16, 1, 16000
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                        input=True, frames_per_buffer=CHUNK)
        buffer.clear()
        while not stop_event.is_set():
            data = stream.read(CHUNK, exception_on_overflow=False)
            buffer.append(np.frombuffer(data, dtype=np.int16))
        stream.stop_stream()
        stream.close()
    finally:
        p.terminate()

async def process_voice_input(user_id, session_id):
    """녹음된 버퍼를 텍스트로 변환하고 서버에 전송합니다."""
    if not st.session_state.audio_buffer: return
    
    with st.spinner("목소리 분석 중..."):
        audio_data = np.concatenate(st.session_state.audio_buffer).astype(np.float32) / 32768.0
        text = await stt_engine.transcribe(audio_data)
        
    if text:
        send_to_server(user_id, session_id, text)

def send_to_server(user_id, session_id, message):
    """서버로 JSON 데이터를 전송합니다."""
    try:
        response = requests.post(
            "http://localhost:8080/api/v1/chat",
            json={"user_id": user_id, "session_id": session_id, "message": message}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.chat_history.append({"role": "user", "content": message})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": data["response"],
                "debug_info": data.get("metadata", {})
            })
    except Exception as e:
        st.error(f"서버 연결 실패: {str(e)}")

# --- [UI 구성] ---
st.title("🤖 Supporter AI 데모")

# 사이드바 설정
with st.sidebar:
    st.header("👤 설정")
    user_id = st.text_input("User ID", value="kwh_01")
    session_id = st.text_input("Session ID", value="sess_01")
    if st.button("🗑️ 대화 초기화"):
        st.session_state.chat_history = []
        st.rerun()

# 1. 채팅 메시지 출력 영역 (고정 높이 및 자동 스크롤)
chat_container = st.container(height=600)

with chat_container:
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])
            
            # AI 답변인 경우 TTS 재생 버튼과 디버그 정보 추가
            if chat["role"] == "assistant":
                col_tts, col_debug = st.columns([1, 4])
                with col_tts:
                    # 각 버튼에 고유한 key 부여 (i 사용)
                    if st.button("🔊 재생", key=f"tts_{i}"):
                        asyncio.run(tts_engine.speak(chat["content"]))
                
                if "debug_info" in chat:
                    with st.expander("🛠️ 디버깅 데이터"):
                        st.json(chat["debug_info"])

# 2. 하단 입력 영역
st.markdown("---")
input_col1, input_col2 = st.columns([1, 5])

with input_col1:
    if not st.session_state.is_recording:
        if st.button("🎙️ 녹음 시작", use_container_width=True):
            st.session_state.is_recording = True
            st.session_state.stop_event.clear()
            st.session_state.audio_buffer = []
            threading.Thread(target=audio_recording_worker, args=(st.session_state.stop_event, st.session_state.audio_buffer)).start()
            st.rerun()
    else:
        if st.button("🛑 전송", type="primary", use_container_width=True):
            st.session_state.stop_event.set()
            st.session_state.is_recording = False
            asyncio.run(process_voice_input(user_id, session_id))
            st.rerun()

with input_col2:
    if prompt := st.chat_input("메시지를 직접 입력하세요..."):
        send_to_server(user_id, session_id, prompt)
        st.rerun()

if st.session_state.is_recording:
    st.toast("녹음 중입니다...", icon="🎙️")