import logging
import signal
import sys
import time
import threading
import os
from datetime import datetime
from src.config_loader import config
from src.utils import setup_logging, ensure_directory_exists
from src.image_processor import ImageProcessor
from src.inference_worker import InferenceWorker
from src.server import F1SuperfanServer


class F1SuperfanApp:
    """Main application class"""

    def __init__(self, config):
        """
        Initialize the application.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = None
        self.image_processor = None
        self.inference_worker = None
        self.server = None
        self.periodic_capture_thread = None
        self.running = False

    def setup_logging(self):
        log_level = self.config.get('logging.level', 'INFO')
        setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        return self.logger

    def initialize_directories(self):
        directories = [
            self.config.get('capture.storage_paths.input'),
            self.config.get('capture.storage_paths.processed'),
            self.config.get('capture.storage_paths.failed')
        ]

        for directory in directories:
            ensure_directory_exists(directory)

    def initialize_components(self):
        # Initialize Image Processor
        self.logger.info("Initializing Image Processor...")
        self.image_processor = ImageProcessor(self.config)
        self.image_processor.start()

        # Initialize Inference Worker
        self.logger.info("Initializing Inference Worker...")
        self.inference_worker = InferenceWorker(self.config, database_handler=None)
        self.inference_worker.start()

        # Initialize Flask server
        self.logger.info("Initializing Flask server...")
        self.server = F1SuperfanServer(self.config, self.image_processor, self.inference_worker)

    def _periodic_capture_loop(self):
        """Periodically captures frames based on config."""
        capture_config = self.config.get('capture', {})
        mode = capture_config.get('mode', 'manual')
        interval = capture_config.get('interval_seconds', 10)

        if mode not in ['periodic', 'both']:
            self.logger.info(f"Periodic capture disabled (mode: {mode})")
            return

        self.logger.info(f"Periodic capture enabled. Interval: {interval} seconds.")
        while self.running:
            try:
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                input_dir = self.config.get('capture.storage_paths.input', 'data/input')
                filename = f"periodic_{timestamp}.jpg"
                output_path = os.path.join(input_dir, filename)

                # Capture frame
                success = self.image_processor.capture_single_frame(output_path)
                if success:
                    self.logger.info(f"Periodic capture successful: {filename}")
                else:
                    self.logger.warning("Periodic capture failed")

                # Wait for the next interval
                time.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error in periodic capture loop: {e}")
                time.sleep(5)  # Wait before retrying on error

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(sig, frame):
            self.logger.info("Shutdown signal received")
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self):
        try:
            self.setup_logging()
            self.running = True

            self.logger.info("=" * 60)
            self.logger.info("F1 Superfan Application Starting")
            self.logger.info("=" * 60)

            # Create directories
            self.initialize_directories()

            # Initialize components
            self.initialize_components()

            # Start periodic capture if enabled
            self.periodic_capture_thread = threading.Thread(target=self._periodic_capture_loop, daemon=True)
            self.periodic_capture_thread.start()

            # Setup signal handlers
            self.setup_signal_handlers()

            self.logger.info("=" * 60)
            self.logger.info("F1 Superfan Application Ready")
            self.logger.info("Access the web interface at http://localhost:5000")
            self.logger.info("=" * 60)

            # Start server (blocking)
            self.server.run()

        except Exception as e:
            if self.logger:
                self.logger.error(f"Fatal error: {e}", exc_info=True)
            else:
                print(f"Fatal error during startup: {e}")
            self.shutdown()
            sys.exit(1)

    def shutdown(self):
        """Gracefully shutdown all components."""
        if self.logger:
            self.logger.info("Shutting down application components...")

        if self.inference_worker:
            self.inference_worker.stop()

        if self.image_processor:
            self.image_processor.stop()

        if self.periodic_capture_thread:
            self.periodic_capture_thread.join(timeout=2.0)

        if self.logger:
            self.logger.info("Application shutdown complete")


def main():
    app = F1SuperfanApp(config)
    app.run()


if __name__ == '__main__':
    main()