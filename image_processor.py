import cv2
import subprocess
import numpy as np
import os
from threading import Lock, Thread
import time


class ImageProcessor:
    def __init__(self):
        self.frame_lock = Lock()
        self.current_frame = None
        self.camera_initialized = False
        self.capture_thread = None

    def capture_single_frame(self):
        """Capture a single frame using GStreamer"""
        try:
            cmd = [
                'gst-launch-1.0',
                'nvarguscamerasrc', 'num-buffers=1',
                '!', 'video/x-raw(memory:NVMM),width=1280,height=720,format=NV12,framerate=30/1',
                '!', 'nvvidconv',
                '!', 'video/x-raw,format=BGRx',
                '!', 'videoconvert',
                '!', 'video/x-raw,format=BGR',
                '!', 'filesink', 'location=/tmp/current_frame.raw'
            ]

            # Run with timeout and suppress output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                print(f"GStreamer error: {result.stderr}")
                return None

            # Check if file exists and has expected size
            if not os.path.exists('/tmp/current_frame.raw'):
                print("Frame file not created")
                return None

            # Read the raw frame data
            with open('/tmp/current_frame.raw', 'rb') as f:
                raw_data = f.read()

            # Convert raw BGR data to numpy array
            # 1280x720x3 = 2,764,800 bytes
            expected_size = 1280 * 720 * 3
            if len(raw_data) != expected_size:
                print(f"Unexpected frame size: {len(raw_data)}, expected: {expected_size}")
                return None

            frame = np.frombuffer(raw_data, dtype=np.uint8)
            frame = frame.reshape((720, 1280, 3))

            # Clean up temporary file
            try:
                os.remove('/tmp/current_frame.raw')
            except:
                pass

            return frame

        except subprocess.TimeoutExpired:
            print("Frame capture timeout")
            return None
        except Exception as e:
            print(f"Frame capture error: {e}")
            return None

    def init_camera(self):
        """Initialize the camera"""
        try:
            print("Initializing camera with GStreamer subprocess...")

            # Test if GStreamer pipeline works
            test_frame = self.capture_single_frame()

            if test_frame is None:
                raise Exception("Failed to capture test frame")

            print(f"GStreamer pipeline test successful! Frame shape: {test_frame.shape}")
            self.camera_initialized = True
            return True

        except Exception as e:
            print(f"Camera initialization failed: {e}")
            return False

    def capture_frames(self):
        """Continuously capture frames in background thread"""
        print("Starting frame capture...")
        while self.camera_initialized:
            try:
                frame = self.capture_single_frame()
                if frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                else:
                    print("Failed to capture frame, retrying...")
                    time.sleep(1)  # Wait longer on failure
                    continue

                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"Frame capture error: {e}")
                time.sleep(1)

    def start(self):
        """Initialize camera and start capture thread"""
        if self.init_camera():
            self.capture_thread = Thread(target=self.capture_frames, daemon=True)
            self.capture_thread.start()
            return True
        else:
            print("WARNING: Camera not available")
            return False

    def get_current_frame(self):
        """Get the current frame (thread-safe)"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None

    def is_initialized(self):
        """Check if camera is initialized"""
        return self.camera_initialized