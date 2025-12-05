import logging
import os
import json
import time
import threading
import base64
import requests
from datetime import datetime
from together import Together
from src.utils import validate_json_structure, ensure_directory_exists

logger = logging.getLogger(__name__)


class InferenceWorker:

    def __init__(self, config, database_handler=None):
        self.config = config
        self.database_handler = database_handler

        self.input_dir = self.config.get('capture.storage_paths.input', 'data/input')
        self.processed_dir = self.config.get('capture.storage_paths.processed', 'data/processed')
        self.failed_dir = self.config.get('capture.storage_paths.failed', 'data/failed')

        self.llm_provider = self.config.get('llm.provider', 'ollama')
        self.ollama_host = self.config.get('llm.ollama_host', 'http://localhost:11434')
        self.ollama_model = self.config.get('llm.ollama_model', 'granite3.2-vision:2b')
        self.together_model = self.config.get('llm.together_model', 'meta-llama/Llama-4-Scout-17B-16E-Instruct')
        self.prompts = self.config.get('llm.prompts', {})

        self.current_race_metadata = self.config.get('race_metadata', {
            'year': datetime.now().year,
            'race_number': 0,
            'circuit_name': 'Unknown',
            'race_id': 0
        })

        self.together_client = None
        if self.llm_provider == 'together':
            self.together_client = Together()

        ensure_directory_exists(self.processed_dir)
        ensure_directory_exists(self.failed_dir)

        self.running = False
        self.processed_files = set()
        self.worker_thread = None

        model = self.together_model if self.llm_provider == 'together' else self.ollama_model
        logger.info(f"InferenceWorker initialized with provider: {self.llm_provider}, model: {model}")
        logger.info(f"Monitoring input directory: {self.input_dir}")
        logger.info(f"Data extraction prompts: {list(self.prompts.keys())}")

    def update_race_metadata(self, new_metadata):
        self.current_race_metadata.update(new_metadata)
        logger.info(f"Updated race metadata: {self.current_race_metadata}")

    def _call_together(self, image_path, prompt):
        try:
            with open(image_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            image_format = os.path.splitext(image_path)[1].lower().replace('.', '')
            if image_format == 'jpg':
                image_format = 'jpeg'

            json_prompt = f"{prompt}\n\nRespond with valid JSON only, no additional text."

            stream = self.together_client.chat.completions.create(
                model=self.together_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": json_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                stream=True,
            )

            response_text = ""
            for chunk in stream:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        response_text += content

            if not response_text:
                logger.error(f"Empty response from Together AI for {image_path}")
                return None

            return response_text

        except Exception as e:
            logger.error(f"Together AI API request failed for {image_path}: {e}")
            return None

    def _call_ollama(self, image_path, prompt):
        try:
            with open(image_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "images": [image_base64],
                "format": "json",
                "stream": False
            }

            url = f"{self.ollama_host}/api/generate"
            response = requests.post(url, json=payload, timeout=90)
            response.raise_for_status()

            result = response.json()

            if 'response' not in result:
                logger.error(f"Invalid response from Ollama: {result}")
                return None

            return result['response']

        except requests.exceptions.Timeout:
            logger.error(f"Ollama API timeout for {image_path}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed for {image_path}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response for {image_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    def _call_llm(self, image_path, prompt):
        if self.llm_provider == 'together':
            return self._call_together(image_path, prompt)
        else:
            return self._call_ollama(image_path, prompt)

    def _process_image(self, image_path):
        logger.info(f"Processing image: {image_path}")

        extraction_results = {
            "image_filename": os.path.basename(image_path),
            "timestamp": datetime.now().isoformat(),
            "race_metadata": self.current_race_metadata.copy(),
            "extractions": {}
        }

        for extraction_type, prompt in self.prompts.items():
            logger.info(f"Extracting {extraction_type} data...")

            response_text = self._call_llm(image_path, prompt)
            if response_text is None:
                return None

            try:
                cleaned_response = self._clean_json_response(response_text)
                response_data = json.loads(cleaned_response)

                required_keys = self._get_required_keys(extraction_type)
                if required_keys:
                    is_valid, error_msg = validate_json_structure(response_data, required_keys)
                    if not is_valid:
                        logger.error(f"Validation failed for {extraction_type}: {error_msg}")
                        self._log_error(image_path, "JSON_VALIDATION_FAILED", error_msg, response_data)
                        return None

                extraction_results["extractions"][extraction_type] = response_data
                logger.info(f"Successfully extracted {extraction_type} data")
                logger.debug(f"Raw response JSON: {response_data}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for {extraction_type}: {e}")
                logger.error(f"Response text: {response_text}")
                logger.error(f"Cleaned text: {cleaned_response if 'cleaned_response' in locals() else 'N/A'}")
                return None

        return extraction_results

    def _clean_json_response(self, response_text):
        cleaned = response_text.strip()

        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned = '\n'.join(lines)

        import re
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)

        return cleaned.strip()

    def _get_required_keys(self, extraction_type):
        if extraction_type == "full_extraction":
            return ["lap_number", "table_type"]

        validation_map = {
            "current_lap": ["lap_number"],
            "timing_table": ["timing_table"],
            "tire_info": []
        }
        return validation_map.get(extraction_type, [])

    def _log_error(self, image_path, error_type, error_message, response_data=None):
        error_log = {
            "timestamp": datetime.now().isoformat(),
            "image_filename": os.path.basename(image_path),
            "error_type": error_type,
            "error_message": error_message,
            "response_data": response_data
        }

        log_filename = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_path = os.path.join(self.failed_dir, log_filename)

        try:
            with open(log_path, 'w') as f:
                json.dump(error_log, f, indent=2)
            logger.error(f"Error log saved: {log_path}")
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")

    def _move_file(self, src_path, dest_dir):
        try:
            dest_path = os.path.join(dest_dir, os.path.basename(src_path))
            os.rename(src_path, dest_path)
            logger.info(f"Moved {src_path} to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file {src_path}: {e}")
            return False

    def _monitor_loop(self):
        logger.info("Starting inference worker monitoring loop...")

        while self.running:
            try:
                input_files = [f for f in os.listdir(self.input_dir)
                               if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

                for filename in input_files:
                    file_path = os.path.join(self.input_dir, filename)

                    if filename in self.processed_files:
                        continue

                    logger.info(f"New image detected: {filename}")

                    results = self._process_image(file_path)

                    if results is None:
                        self._log_error(file_path, "PROCESSING_FAILED",
                                        "Image processing failed")
                        self._move_file(file_path, self.failed_dir)
                    else:
                        self.processed_files.add(filename)

                        if self.database_handler:
                            try:
                                self.database_handler.save_extraction_results(results)
                            except Exception as e:
                                logger.error(f"Failed to save to database: {e}")
                                self._log_error(file_path, "DATABASE_ERROR",
                                                f"Failed to save to database: {e}")
                                continue

                        self._move_file(file_path, self.processed_dir)

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def start(self):
        if self.running:
            logger.warning("Inference worker already running")
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Inference worker started")

    def stop(self):
        if not self.running:
            logger.warning("Inference worker not running")
            return

        logger.info("Stopping inference worker...")
        self.running = False

        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)

        logger.info("Inference worker stopped")