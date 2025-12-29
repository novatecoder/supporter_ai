import pytest
import os
import asyncio
from supporter_ai.expression.tts_engine import TTSEngine

@pytest.fixture
def tts_engine():
    """테스트용 TTS 엔진 인스턴스 제공"""
    return TTSEngine()

@pytest.mark.asyncio
async def test_tts_engine_initialization(tts_engine):
    """엔진 초기화 확인"""
    assert tts_engine.voice == "ko-KR-SunHiNeural"

@pytest.mark.asyncio
async def test_tts_speak_logic(tts_engine, mocker):
    """
    TTS 재생 로직이 에러 없이 실행되는지 테스트
    (실제 스피커 출력을 확인하기 어려우므로 pygame 호출 여부를 mock으로 확인 가능)
    """
    # 텍스트가 비어있을 때 처리 확인
    await tts_engine.speak("")
    
    # 실제 재생 테스트 (네트워크 연결 필요)
    # 너무 길면 테스트 시간이 늘어나므로 짧은 단어로 테스트
    try:
        await tts_engine.speak("테스트")
    except Exception as e:
        pytest.fail(f"TTS 재생 중 에러 발생: {e}")

@pytest.mark.manual
@pytest.mark.asyncio
async def test_tts_manual_playback(tts_engine):
    """실제로 소리가 나는지 확인하는 수동 테스트"""
    print("\n[수동 테스트] 소리가 잘 들리는지 확인하세요.")
    test_text = "안녕하세요"
    await tts_engine.speak(test_text)