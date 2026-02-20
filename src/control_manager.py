import threading
import json
import os


class ControlManager:
    def __init__(self):
        self.lock = threading.Lock()
        self._capture_enabled = False
        self._inference_enabled = False
        self._load_state()

    def _load_state(self):
        try:
            state_file = "data/control_states.json"
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    loaded_state = json.load(f)
                    self._capture_enabled = loaded_state.get("capture_enabled", False)
                    self._inference_enabled = loaded_state.get(
                        "inference_enabled", False
                    )
        except Exception as e:
            print(f"Error loading control states: {e}")

    def _save_state(self):
        state = {
            "capture_enabled": self._capture_enabled,
            "inference_enabled": self._inference_enabled,
        }
        try:
            with open("data/control_states.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving control states: {e}")

    @property
    def capture_enabled(self):
        with self.lock:
            return self._capture_enabled

    @property
    def inference_enabled(self):
        with self.lock:
            return self._inference_enabled

    def set_capture(self, enabled):
        with self.lock:
            self._capture_enabled = enabled
            self._save_state()

    def set_inference(self, enabled):
        with self.lock:
            self._inference_enabled = enabled
            self._save_state()

    def toggle_capture(self):
        with self.lock:
            self._capture_enabled = not self._capture_enabled
            self._save_state()
            return self._capture_enabled

    def toggle_inference(self):
        with self.lock:
            self._inference_enabled = not self._inference_enabled
            self._save_state()
            return self._inference_enabled


control_manager = ControlManager()
