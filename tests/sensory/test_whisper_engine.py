import os
import pytest
import numpy as np
import torch
import whisper
from supporter_ai.sensory.whisper_engine import WhisperEngine

@pytest.fixture
def engine():
    """테스트용 Whisper 엔진 인스턴스 제공"""
    return WhisperEngine()

@pytest.mark.asyncio
async def test_whisper_load_and_unload(engine):
    """모델 로드 및 언로드 기능 테스트"""
    # 1. 로드 테스트
    engine.load_model()
    assert engine.model is not None
    assert engine.device in ["cuda", "cpu"]
    
    # 2. 언로드 테스트
    engine.unload_model()
    assert engine.model is None
    # GPU 메모리 해제 확인 (CUDA 환경인 경우만)
    if torch.cuda.is_available():
        assert torch.cuda.memory_allocated() == 0

@pytest.mark.asyncio
async def test_transcribe_with_sample_file(engine):
    """
    저장된 오디오 파일을 읽어 텍스트로 잘 변환되는지 테스트
    (tests/sensory/assets/sample.wav 파일이 있다고 가정)
    """
    test_audio_path = "tests/sensory/assets/sample.wav"
    
    if not os.path.exists(test_audio_path):
        pytest.skip("테스트용 오디오 파일이 존재하지 않아 스킵합니다.")

    # whisper.load_audio는 파일을 float32 numpy 배열로 읽어옵니다.
    audio = whisper.load_audio(test_audio_path)
    result_text = await engine.transcribe(audio)
    
    assert isinstance(result_text, str)
    assert len(result_text) > 0
    print(f"\n[파일 변환 결과]: {result_text}")

# --- [수동 마이크 테스트] ---
# pytest 실행 시 기본적으로 무시되며, 수동으로 지정할 때만 실행됩니다.
@pytest.mark.manual
@pytest.mark.asyncio
async def test_microphone_manual_realtime(engine):
    """
    실제 마이크 입력을 3초간 받아 텍스트로 변환하는 수동 테스트
    """
    import pyaudio
    
    # 오디오 설정
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 3

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("\n" + "="*30)
    print(" [마이크 테스트] 3초간 말씀해 주세요...")
    print("="*30)
    
    frames = []
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(np.frombuffer(data, dtype=np.int16))

    print("녹음 완료. 변환 중...")
    
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Whisper 입력 형식에 맞게 데이터 변환 (정규화된 float32)
    audio_data = np.concatenate(frames).astype(np.float32) / 32768.0
    
    result_text = await engine.transcribe(audio_data)
    
    print(f"\n[마이크 인식 결과]: {result_text}")
    assert isinstance(result_text, str)