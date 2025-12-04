import yaml
from pathlib import Path


class Config:
    """Application config loader."""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self.load_config()

    def load_config(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)
        self._validate_config()

    def _validate_config(self):
        required_sections = ['camera', 'capture', 'llm', 'database', 'logging']
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")

    def get(self, key_path, default=None):
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    @property
    def camera(self):
        return self._config.get('camera', {})

    @property
    def capture(self):
        return self._config.get('capture', {})

    @property
    def llm(self):
        return self._config.get('llm', {})

    @property
    def database(self):
        return self._config.get('database', {})

    @property
    def logging_config(self):
        return self._config.get('logging', {})


config = Config()