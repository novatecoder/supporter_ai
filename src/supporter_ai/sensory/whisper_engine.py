import whisper
import torch
import logging
import numpy as np
from supporter_ai.common.config import settings

logger = logging.getLogger(__name__)

class WhisperEngine:
    def __init__(self):
        self.model_name = settings.WHISPER_MODEL_NAME
        self.device = settings.WHISPER_DEVICE if torch.cuda.is_available() else "cpu"
        self.model = None

    def load_model(self):
        """필요할 때 모델을 GPU 메모리에 로드합니다."""
        if self.model is None:
            logger.info(f"Whisper 모델 로딩 중: {self.model_name} ({self.device})")
            # RTX 4070의 VRAM을 아끼기 위해 fp16 연산을 기본으로 사용합니다.
            self.model = whisper.load_model(self.model_name, device=self.device)
            logger.info("Whisper 모델 로드 완료.")

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        입력된 오디오 배열을 텍스트로 변환합니다.
        :param audio_data: float32 형태의 오디오 샘플 배열
        """
        self.load_model()
        
        try:
            # 한국어 인식을 우선적으로 처리하도록 설정
            result = self.model.transcribe(
                audio_data, 
                language="ko", 
                fp16=True if self.device == "cuda" else False
            )
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"STT 변환 실패: {e}")
            return ""

    def unload_model(self):
        """VRAM 확보가 필요할 경우 모델을 메모리에서 내립니다."""
        self.model = None
        if self.device == "cuda":
            torch.cuda.empty_cache()
        logger.info("Whisper 모델이 VRAM에서 해제되었습니다.")