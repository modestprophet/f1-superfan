from flask import Flask, render_template, Response, jsonify, request
import cv2
import base64
from threading import Lock, Thread
import ollama
import time
import subprocess
import numpy as np
import os

app = Flask(__name__)

# Camera configuration
frame_lock = Lock()
current_frame = None
camera_initialized = False


def capture_single_frame():
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


def init_camera():
    global camera_initialized

    try:
        print("Initializing camera with GStreamer subprocess...")

        # Test if GStreamer pipeline works
        test_frame = capture_single_frame()

        if test_frame is None:
            raise Exception("Failed to capture test frame")

        print(f"GStreamer pipeline test successful! Frame shape: {test_frame.shape}")
        camera_initialized = True
        return True

    except Exception as e:
        print(f"Camera initialization failed: {e}")
        return False


def capture_frames():
    global current_frame

    print("Starting frame capture...")
    while camera_initialized:
        try:
            frame = capture_single_frame()
            if frame is not None:
                with frame_lock:
                    current_frame = frame.copy()
            else:
                print("Failed to capture frame, retrying...")
                time.sleep(1)  # Wait longer on failure
                continue

            time.sleep(0.033)  # ~30 FPS
        except Exception as e:
            print(f"Frame capture error: {e}")
            time.sleep(1)


# Initialize camera and start capture thread
if init_camera():
    capture_thread = Thread(target=capture_frames, daemon=True)
    capture_thread.start()
else:
    print("WARNING: Camera not available")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with frame_lock:
                if current_frame is not None:
                    ret, buffer = cv2.imencode('.jpg', current_frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)  # ~30 FPS

    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture_and_infer', methods=['POST'])
def capture_and_infer():
    try:
        if not camera_initialized:
            return jsonify({'error': 'Camera not available'}), 503

        data = request.json
        ollama_host = data.get('ollama_host', 'http://localhost:11434')
        model_name = data.get('model', 'llava')
        prompt = data.get('prompt', 'Describe this image')

        # Capture current frame
        with frame_lock:
            if current_frame is None:
                return jsonify({'error': 'No frame available'}), 400
            frame = current_frame.copy()

        # Convert frame to base64 for response
        _, buffer = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        # Save frame for ollama
        temp_path = '/tmp/capture.jpg'
        cv2.imwrite(temp_path, frame)

        # Run inference
        client = ollama.Client(host=ollama_host)
        response_text = ""

        stream = client.chat(
            model=model_name,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [temp_path]
            }],
            stream=True,
        )

        for chunk in stream:
            response_text += chunk["message"]["content"]

        return jsonify({
            'response': response_text,
            'image': f'data:image/jpeg;base64,{img_base64}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)