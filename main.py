import logging
import signal
import sys
from src.config_loader import config
from src.utils import setup_logging, ensure_directory_exists
from src.image_processor import ImageProcessor
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
        self.server = None

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

        # Initialize Flask server
        self.logger.info("Initializing Flask server...")
        self.server = F1SuperfanServer(self.config, self.image_processor)

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

            self.logger.info("=" * 60)
            self.logger.info("F1 Superfan Application Starting")
            self.logger.info("=" * 60)

            # Create directories
            self.initialize_directories()

            # Initialize components
            self.initialize_components()

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

        if self.image_processor:
            self.image_processor.stop()

        if self.logger:
            self.logger.info("Application shutdown complete")


def main():
    app = F1SuperfanApp(config)
    app.run()


if __name__ == '__main__':
    main()