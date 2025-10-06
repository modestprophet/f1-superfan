import cv2
import threading
import logging
import os

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles camera capture and frame management using GStreamer."""

    def __init__(self, config):
        """
        Initialize the ImageProcessor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.cap = None
        self.current_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.capture_thread = None
        self._initialized = False

        resolution = self.config.get('camera.resolution', '1280x720')
        fps = self.config.get('camera.fps', 30)

        self.width, self.height = map(int, resolution.split('x'))
        self.fps = fps

        logger.info(f"ImageProcessor initialized with resolution: {resolution}, FPS: {fps}")

    def start(self):
        """Start the camera capture thread."""
        if self.running:
            logger.warning("ImageProcessor already running")
            return

        try:
            gst_pipeline = (
                f"nvarguscamerasrc ! "
                f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
                f"format=NV12, framerate={self.fps}/1 ! "
                f"nvvidconv ! video/x-raw, format=BGRx ! "
                f"videoconvert ! video/x-raw, format=BGR ! "
                f"appsink drop=1"
            )

            logger.info(f"Opening camera with GStreamer pipeline")
            self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

            if not self.cap.isOpened():
                logger.error("Failed to open camera")
                return

            self._initialized = True
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            logger.info("Camera capture started successfully")

        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            self._initialized = False

    def _capture_loop(self):
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.current_frame = frame.copy()
                else:
                    logger.warning("Failed to capture frame")
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")

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

        if self.cap:
            self.cap.release()

        logger.info("Camera capture stopped")

