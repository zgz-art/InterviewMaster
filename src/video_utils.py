import os
import cv2
import threading
from av import VideoFrame
from streamlit_webrtc import VideoProcessorBase
from src.config import FRAME_CAPTURE_INTERVAL, CAPTURE_DIR

os.makedirs(CAPTURE_DIR, exist_ok=True)

class InterviewVideoProcessor(VideoProcessorBase):
    """处理 WebRTC 视频帧，按间隔抽帧保存。"""
    def __init__(self):
        self.frame_count = 0
        self.lock = threading.Lock()

    def recv(self, frame: VideoFrame) -> VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        with self.lock:
            self.frame_count += 1
            if self.frame_count % FRAME_CAPTURE_INTERVAL == 0:
                path = os.path.join(CAPTURE_DIR, f"frame_{self.frame_count}.jpg")
                cv2.imwrite(path, img)
        return frame
