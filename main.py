import logging
import signal
import sys
from src.config_loader import config
from src.utils import setup_logging, ensure_directory_exists
from src.image_processor import ImageProcessor
from src.server import F1SuperfanServer

logger = None
image_processor = None


def signal_handler(sig, frame):
    logger.info("Shutdown signal received")
    if image_processor:
        image_processor.stop()
    sys.exit(0)


def main():
    global logger, image_processor

    try:
        # Load configuration
        print("Loading configuration...")

        # Setup logging
        log_level = config.get('logging.level', 'INFO')
        setup_logging(log_level)
        logger = logging.getLogger(__name__)

        logger.info("=" * 60)
        logger.info("F1 Superfan Application Starting")
        logger.info("=" * 60)

        # Ensure directories exist
        logger.info("Creating data directories...")
        ensure_directory_exists(config.get('capture.storage_paths.input'))
        ensure_directory_exists(config.get('capture.storage_paths.processed'))
        ensure_directory_exists(config.get('capture.storage_paths.failed'))

        # Initialize Image Processor
        logger.info("Initializing Image Processor...")
        image_processor = ImageProcessor(config)
        image_processor.start()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize and start Flask server
        logger.info("Initializing Flask server...")
        server = F1SuperfanServer(config, image_processor)

        logger.info("=" * 60)
        logger.info("F1 Superfan Application Ready")
        logger.info("Access the web interface at http://localhost:5000")
        logger.info("=" * 60)

        # Start server (blocking)
        server.run()

    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error during startup: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()