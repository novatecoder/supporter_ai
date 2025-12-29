import asyncio
import edge_tts
import pygame
import os
import logging
import tempfile

logger = logging.getLogger(__name__)

class TTSEngine:
    def __init__(self, voice="ko-KR-SunHiNeural"):
        self.voice = voice
        # pygame 오디오 믹서 초기화
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    async def speak(self, text: str):
        """텍스트를 음성으로 변환하고 즉시 재생합니다."""
        if not text:
            return

        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name

        try:
            # 1. 음성 파일 생성
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(tmp_path)

            # 2. 재생
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            # 재생이 끝날 때까지 대기
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"TTS 재생 실패: {e}")
        finally:
            # 재생 종료 후 파일 삭제
            pygame.mixer.music.unload()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def stop(self):
        """현재 재생 중인 음성을 중지합니다."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()