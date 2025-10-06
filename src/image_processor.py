import cv2
import threading
import logging
import os
import subprocess
import numpy as np
import time

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles camera capture and frame management using GStreamer subprocess."""

    def __init__(self, config):
        """
        Initialize the ImageProcessor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.current_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.capture_thread = None
        self._initialized = False

        resolution = self.config.get('camera.resolution', '1280x720')
        fps = self.config.get('camera.fps', 30)

        self.width, self.height = map(int, resolution.split('x'))
        self.fps = fps
        self.temp_frame_path = '/tmp/current_frame.raw'

        logger.info(f"ImageProcessor initialized with resolution: {self.width}x{self.height}, FPS: {self.fps}")

    def _capture_single_frame_subprocess(self):
        """Capture a single frame using GStreamer subprocess."""
        try:
            cmd = [
                'gst-launch-1.0',
                'nvarguscamerasrc', 'num-buffers=1', '!',
                f'video/x-raw(memory:NVMM),width={self.width},height={self.height},format=NV12,framerate={self.fps}/1', '!',
                'nvvidconv', '!',
                'video/x-raw,format=BGRx', '!',
                'videoconvert', '!',
                'video/x-raw,format=BGR', '!',
                'filesink', f'location={self.temp_frame_path}'
            ]

            # Run with timeout and suppress output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                logger.error(f"GStreamer error: {result.stderr}")
                return None

            if not os.path.exists(self.temp_frame_path):
                logger.error("Frame file not created")
                return None

            with open(self.temp_frame_path, 'rb') as f:
                raw_data = f.read()

            expected_size = self.width * self.height * 3
            if len(raw_data) != expected_size:
                logger.error(f"Unexpected frame size: {len(raw_data)}, expected: {expected_size}")
                return None

            frame = np.frombuffer(raw_data, dtype=np.uint8).reshape((self.height, self.width, 3))
            try:
                os.remove(self.temp_frame_path)
            except OSError as e:
                logger.warning(f"Could not remove temp frame file: {e}")
            return frame

        except subprocess.TimeoutExpired:
            logger.error("Frame capture timeout")
            return None
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None

    def start(self):
        """Start the camera capture thread."""
        if self.running:
            logger.warning("ImageProcessor already running")
            return
        try:
            logger.info("Initializing camera with GStreamer subprocess test...")
            test_frame = self._capture_single_frame_subprocess()
            if test_frame is None:
                raise Exception("Failed to capture test frame")

            logger.info(f"GStreamer pipeline test successful! Frame shape: {test_frame.shape}")
            self._initialized = True

            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            logger.info("Camera capture started successfully")
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            self._initialized = False

    def _capture_loop(self):
        logger.info("Starting frame capture loop...")
        while self.running:
            try:
                frame = self._capture_single_frame_subprocess()
                if frame is not None:
                    with self.lock:
                        self.current_frame = frame.copy()
                else:
                    logger.warning("Failed to capture frame in loop, retrying...")
                    time.sleep(1)
                    continue

                # Capturing via subprocess has significant overhead.
                # This sleep will result in a lower actual FPS.
                time.sleep(1.0 / self.fps)
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(1)

    def get_current_frame(self):
        with self.lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def capture_single_frame(self, output_path):
        try:
            frame = self.get_current_frame()
            if frame is None:
                logger.error("No frame available for capture")
                return False

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            success = cv2.imwrite(output_path, frame)
            if success:
                logger.info(f"Frame captured and saved to: {output_path}")
            else:
                logger.error(f"Failed to save frame to: {output_path}")

            return success

        except Exception as e:
            logger.error(f"Error capturing single frame: {e}")
            return False

    def is_initialized(self):
        return self._initialized

    def stop(self):
        logger.info("Stopping camera capture")
        self.running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)

        logger.info("Camera capture stopped")

