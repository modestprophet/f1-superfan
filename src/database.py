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
    year = Column(Integer, nullable=True)
    race_number = Column(Integer, nullable=True)
    circuit_name = Column(String(100), nullable=True)
    race_id = Column(Integer, nullable=True)
    lap_number = Column(Integer, nullable=True)
    table_type = Column(String(50), nullable=True)
    data_json = Column(Text, nullable=True)
    processing_status = Column(String(20), default='new')

    def __repr__(self):
        return f"<InferenceResult(id={self.id}, lap={self.lap_number}, type={self.table_type}, race={self.race_number})>"


class DatabaseHandler:
    """Handles database connections and operations."""

    def __init__(self, config):
        self.config = config
        db_path = self.config.get('database.path', 'data/f1_data.db')

        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(db_url, echo=False)
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
            extractions = raw_results.get('extractions', {})
            if not extractions:
                return

            # Get race metadata
            race_metadata = raw_results.get('race_metadata', {})

            key = next(iter(extractions))
            data = extractions[key]

            lap_number = data.get('lap_number')
            table_type = data.get('table_type')
            timing_data = data.get('timing_data', data.get('timing_table', data))

            record = InferenceResult(
                timestamp=datetime.now(),
                year=race_metadata.get('year'),
                race_number=race_metadata.get('race_number'),
                circuit_name=race_metadata.get('circuit_name'),
                race_id=race_metadata.get('race_id'),
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

