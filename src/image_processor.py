import cv2
import threading
import logging
import os
import subprocess
import numpy as np
import time

logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self, config):
        self.config = config
        self.current_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.capture_thread = None
        self._initialized = False

        resolution = self.config.get("camera.resolution", "1280x720")
        fps = self.config.get("camera.fps", 30)
        self.rotation = self.config.get("camera.rotation", 0)

        self.width, self.height = map(int, resolution.split("x"))
        self.fps = fps
        self.temp_frame_path = "/tmp/current_frame.raw"

    def _capture_single_frame_subprocess(self):
        try:
            flip_method = 2 if self.rotation == 180 else 0

            cmd = [
                "gst-launch-1.0",
                "nvarguscamerasrc",
                "num-buffers=1",
                "!",
                f"video/x-raw(memory:NVMM),width={self.width},height={self.height},format=NV12,framerate={self.fps}/1",
                "!",
                "nvvidconv",
                f"flip-method={flip_method}",
                "!",
                "video/x-raw,format=BGRx",
                "!",
                "videoconvert",
                "!",
                "video/x-raw,format=BGR",
                "!",
                "filesink",
                f"location={self.temp_frame_path}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                logger.error(f"GStreamer error: {result.stderr}")
                return None

            with open(self.temp_frame_path, "rb") as f:
                raw_data = f.read()

            frame = np.frombuffer(raw_data, dtype=np.uint8).reshape(
                (self.height, self.width, 3)
            )
            os.remove(self.temp_frame_path)
            return frame

        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None

    def start(self):
        if self.running:
            return

        test_frame = self._capture_single_frame_subprocess()
        if test_frame is None:
            logger.error("Failed to capture test frame")
            return

        self._initialized = True
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def _capture_loop(self):
        while self.running:
            frame = self._capture_single_frame_subprocess()
            if frame is not None:
                with self.lock:
                    self.current_frame = frame.copy()
            else:
                time.sleep(1)
                continue

            time.sleep(1.0 / self.fps)

    def get_current_frame(self):
        with self.lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def capture_single_frame(self, output_path):
        frame = self.get_current_frame()
        if frame is None:
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return cv2.imwrite(output_path, frame)

    def is_initialized(self):
        return self._initialized

    def stop(self):
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
