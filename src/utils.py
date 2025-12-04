import logging
import os
import sys


def setup_logging(log_level='INFO'):
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


def validate_json_structure(data, required_keys):
    if not isinstance(data, dict):
        return False, "Data is not a valid dictionary"

    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        return False, f"Missing required keys: {', '.join(missing_keys)}"

    return True, None


def ensure_directory_exists(directory_path):
    os.makedirs(directory_path, exist_ok=True)