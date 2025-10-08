from flask import Flask, render_template, Response, jsonify, request
import cv2
import time
import logging
from datetime import datetime
import os
import tempfile

logger = logging.getLogger(__name__)


class F1SuperfanServer:
    """Flask web server for F1 Superfan application."""

    def __init__(self, config, image_processor, inference_worker=None):
        """
        Initialize the Flask server.

        Args:
            config: Configuration object
            image_processor: ImageProcessor instance
            inference_worker: InferenceWorker instance
        """
        self.config = config
        self.image_processor = image_processor
        self.inference_worker = inference_worker

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        template_folder = os.path.join(project_root, 'templates')
        static_folder = os.path.join(project_root, 'static')

        self.app = Flask(__name__,
                         template_folder=template_folder,
                         static_folder=static_folder)

        self._register_routes()

        logger.info("Flask server initialized")

    def _register_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_video_stream(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/manual_capture', methods=['POST'])
        def manual_capture():
            """Manually trigger a frame capture."""
            try:
                if not self.image_processor.is_initialized():
                    return jsonify({'error': 'Camera not available'}), 503

                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                input_dir = self.config.get('capture.storage_paths.input', 'data/input')
                filename = f"manual_{timestamp}.jpg"
                output_path = os.path.join(input_dir, filename)

                # Capture frame
                success = self.image_processor.capture_single_frame(output_path)

                if success:
                    logger.info(f"Manual capture successful: {filename}")
                    return jsonify({
                        'success': True,
                        'filename': filename,
                        'message': 'Frame captured successfully'
                    })
                else:
                    return jsonify({'error': 'Failed to capture frame'}), 500

            except Exception as e:
                logger.error(f"Error in manual capture: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/adhoc_inference', methods=['POST'])
        def adhoc_inference():
            """Perform ad hoc inference with custom prompt."""
            try:
                if not self.image_processor.is_initialized():
                    return jsonify({'error': 'Camera not available'}), 503

                if not self.inference_worker:
                    return jsonify({'error': 'Inference worker not available'}), 503

                # Get custom prompt from request
                data = request.get_json()
                custom_prompt = data.get('prompt', 'describe the numerical data you see in this image')

                if not custom_prompt:
                    return jsonify({'error': 'Prompt is required'}), 400

                logger.info(f"Ad hoc inference requested with prompt: {custom_prompt}")

                # Capture frame to temporary file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_path = temp_file.name

                success = self.image_processor.capture_single_frame(temp_path)

                if not success:
                    return jsonify({'error': 'Failed to capture frame'}), 500

                # Call Ollama with custom prompt
                response_text = self.inference_worker._call_llm(temp_path, custom_prompt)

                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")

                if response_text is None:
                    return jsonify({'error': 'Inference failed'}), 500

                logger.info(f"Ad hoc inference successful")
                return jsonify({
                    'success': True,
                    'response': response_text,
                    'prompt': custom_prompt
                })

            except Exception as e:
                logger.error(f"Error in ad hoc inference: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/status')
        def status():
            """Get system status."""
            return jsonify({
                'camera_initialized': self.image_processor.is_initialized(),
                'inference_worker_running': self.inference_worker.running if self.inference_worker else False,
                'capture_mode': self.config.get('capture.mode', 'unknown')
            })

    def _generate_video_stream(self):
        while True:
            frame = self.image_processor.get_current_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)  # ~30 FPS

    def run(self, host='0.0.0.0', port=5000):
        """
        Start the Flask server.

        Args:
            host: Host address
            port: Port number
        """
        logger.info(f"Starting Flask server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False, threaded=True)