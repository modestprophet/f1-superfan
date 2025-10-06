from flask import Flask, render_template, Response, jsonify, request
import cv2
import base64
import ollama
import time
from image_processor import ImageProcessor

app = Flask(__name__)

# Initialize image processor
image_processor = ImageProcessor()
image_processor.start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = image_processor.get_current_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
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
        if not image_processor.is_initialized():
            return jsonify({'error': 'Camera not available'}), 503

        data = request.json
        ollama_host = data.get('ollama_host', 'http://localhost:11434')
        model_name = data.get('model', 'llava')
        prompt = data.get('prompt', 'Describe this image')

        # Capture current frame
        frame = image_processor.get_current_frame()
        if frame is None:
            return jsonify({'error': 'No frame available'}), 400

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