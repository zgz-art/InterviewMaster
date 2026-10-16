import asyncio
import tempfile
import edge_tts
from faster_whisper import WhisperModel
from src.config import WHISPER_MODEL_SIZE

# 全局 Whisper 模型（懒加载）
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model

def transcribe_audio(audio_bytes: bytes) -> str:
    """将音频字节流转录为文本。"""
    model = get_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    segments, _ = model.transcribe(tmp_path, language="zh", beam_size=5)
    text = "".join(seg.text for seg in segments)
    return text.strip()

async def _tts_async(text: str, output_path: str):
    """异步生成语音文件。"""
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
    await communicate.save(output_path)

def text_to_speech(text: str) -> str:
    """文本转语音，返回生成的音频文件路径。"""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        output_path = f.name
    asyncio.run(_tts_async(text, output_path))
    return output_path
