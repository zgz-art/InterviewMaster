import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------- 智谱 GLM 配置 ----------
# 优先从 Streamlit Secrets 读取，兼容本地 .env
try:
    OPENAI_API_KEY = st.secrets.get("ZHIPU_API_KEY", os.getenv("ZHIPU_API_KEY"))
    OPENAI_BASE_URL = st.secrets.get("ZHIPU_BASE_URL", os.getenv(
        "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"
    ))
    OPENAI_MODEL = st.secrets.get("ZHIPU_MODEL", os.getenv("ZHIPU_MODEL", "glm-4-flash"))
except:
    OPENAI_API_KEY = os.getenv("ZHIPU_API_KEY")
    OPENAI_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
    OPENAI_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
FRAME_CAPTURE_INTERVAL = 300
CAPTURE_DIR = "captures"
