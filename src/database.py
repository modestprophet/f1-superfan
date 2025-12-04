from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()


class InferenceResult(Base):
    """Database model for storing inference results."""
    __tablename__ = 'inference_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    lap_number = Column(Integer, nullable=True)
    table_type = Column(String(50), nullable=True)  # 'interval', 'gap', 'tire_age'
    data_json = Column(Text, nullable=True)
    processing_status = Column(String(20), default='new')

    def __repr__(self):
        return f"<InferenceResult(id={self.id}, lap={self.lap_number}, type={self.table_type})>"


class DatabaseHandler:
    """Handles database connections and operations."""

    def __init__(self, config):
        self.config = config
        db_path = self.config.get('database.path', 'data/f1_data.db')

        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # Initialize SQLite engine
        db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(db_url, echo=False)

        # Create tables
        Base.metadata.create_all(self.engine)

        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized at {db_path}")

    def save_extraction_results(self, raw_results):
        """
        Save extraction results to the database.

        Args:
            raw_results (dict): The dictionary returned by InferenceWorker._process_image
        """
        session = self.Session()
        try:
            # Depending on how the prompts are keyed in config, we might have one or more extractions.
            # Based on the requirement for a monolithic prompt, we assume the relevant data
            # is inside one of the extraction keys (e.g., 'full_extraction').

            extractions = raw_results.get('extractions', {})

            # Flatten the first extraction found (assuming monolithic prompt)
            if not extractions:
                logger.warning("No extractions found to save.")
                return

            # Take the first available extraction result
            # We expect the structure: { "lap_number": X, "table_type": "...", "timing_data": ... }
            key = next(iter(extractions))
            data = extractions[key]

            lap_number = data.get('lap_number')
            table_type = data.get('table_type')

            # content might be under 'timing_data', 'data', or 'timing_table' depending on LLM output
            # We'll serialize the whole data object minus lap/type for data_json,
            # or specifically look for the table list.
            timing_data = data.get('timing_data') or data.get('timing_table') or data

            # Create record
            record = InferenceResult(
                timestamp=datetime.now(),
                lap_number=lap_number,
                table_type=table_type,
                data_json=json.dumps(timing_data),
                processing_status='new'
            )

            session.add(record)
            session.commit()
            logger.info(f"Saved inference result to database (ID: {record.id})")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save to database: {e}")
            raise
        finally:
            session.close()

