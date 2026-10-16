import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# 视频抽帧间隔（帧数），约 30fps 下 300 帧 ≈ 10 秒
FRAME_CAPTURE_INTERVAL = 300
# 抽帧保存目录
CAPTURE_DIR = "captures"
