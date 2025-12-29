import streamlit as st
import requests
import json

# 페이지 설정
st.set_page_config(page_title="Supporter AI Debug Console", layout="wide")

st.title("🤖 Supporter AI 데모")
st.markdown("> **디버깅 모드:** 답변 하단의 익스팬더를 열어 AI의 내부 상태를 확인할 수 있습니다.")
st.markdown("---")

# 사이드바 설정
with st.sidebar:
    st.header("👤 설정")
    user_id = st.text_input("User ID", value="kwh_01")
    session_id = st.text_input("Session ID", value="sess_01")
    if st.button("🗑️ 대화 초기화"):
        st.session_state.chat_history = []
        st.rerun()

# 채팅 기록 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 기존 대화 출력
for chat in st.session_state.chat_history:
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])
        # AI 답변에만 디버그 정보 표시
        if chat["role"] == "assistant" and "debug_info" in chat:
            with st.expander("🛠️ 디버깅 데이터 (PAC 상태 / 권한 / 요약)"):
                st.json(chat["debug_info"])

# 채팅 입력
if prompt := st.chat_input("메시지를 입력하세요..."):
    # 1. 사용자 메시지 추가
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI 답변 요청
    with st.chat_message("assistant"):
        try:
            response = requests.post(
                "http://localhost:8080/api/v1/chat",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": prompt
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["response"]
                metadata = data.get("metadata", {})

                # 답변은 바로 출력
                st.markdown(answer)
                
                # 디버깅 정보는 접어서 출력
                with st.expander("🛠️ 디버깅 데이터 (PAC 상태 / 권한 / 요약)"):
                    st.json(metadata)
                
                # 기록 저장
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "debug_info": metadata
                })
            else:
                st.error(f"서버 에러: {response.text}")
        except Exception as e:
            st.error(f"연결 실패: {str(e)}")