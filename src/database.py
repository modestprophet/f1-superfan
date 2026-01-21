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
    safety_car_status = Column(Integer, default=0)
    data_json = Column(Text, nullable=True)
    processing_status = Column(String(20), default='new')

    def __repr__(self):
        return f"<InferenceResult(id={self.id}, lap={self.lap_number}, type={self.table_type}, race={self.race_number})>"


class RaceTimingData(Base):
    """Parsed and normalized race timing data."""
    __tablename__ = 'race_timing_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    inference_result_id = Column(Integer, nullable=False)

    timestamp = Column(DateTime, default=datetime.now)
    year = Column(Integer, nullable=True)
    race_number = Column(Integer, nullable=True)
    circuit_name = Column(String(100), nullable=True)
    race_id = Column(Integer, nullable=True)
    lap_number = Column(Integer, nullable=False)

    position = Column(Integer, nullable=False)
    driver_code = Column(String(3), nullable=False)
    tire_compound = Column(String(1), nullable=True)

    gap_to_leader = Column(String(20), nullable=True)
    interval = Column(String(20), nullable=True)
    tire_age = Column(Integer, nullable=True)
    pitstop_count = Column(Integer, nullable=True)

    is_in_pit = Column(Integer, default=0)
    is_out = Column(Integer, default=0)
    is_safety_car = Column(Integer, default=0)
    is_under_investigation = Column(Integer, default=0)
    has_penalty = Column(Integer, default=0)

    table_type = Column(String(20), nullable=False)

    def __repr__(self):
        return f"<RaceTimingData(lap={self.lap_number}, pos={self.position}, driver={self.driver_code}, type={self.table_type})>"


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
        session = self.Session()
        try:
            extractions = raw_results.get('extractions', {})
            if not extractions:
                return

            race_metadata = raw_results.get('race_metadata', {})
            key = next(iter(extractions))
            data = extractions[key]

            record = InferenceResult(
                timestamp=datetime.now(),
                year=race_metadata.get('year'),
                race_number=race_metadata.get('race_number'),
                circuit_name=race_metadata.get('circuit_name'),
                race_id=race_metadata.get('race_id'),
                lap_number=data.get('lap_number'),
                table_type=data.get('table_type'),
                safety_car_status=1 if data.get('safety_car') else 0,
                data_json=json.dumps(data.get('timing_data', data.get('timing_table', data))),
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

    def get_unprocessed_results(self):
        session = self.Session()
        try:
            results = session.query(InferenceResult).filter(
                InferenceResult.processing_status == 'new'
            ).order_by(InferenceResult.timestamp.asc()).all()

            logger.info(f"Found {len(results)} unprocessed inference results")
            return results
        finally:
            session.close()

    def update_processing_status(self, inference_result_id, status):
        session = self.Session()
        try:
            record = session.query(InferenceResult).filter(
                InferenceResult.id == inference_result_id
            ).first()

            if record:
                record.processing_status = status
                session.commit()
                logger.info(f"Updated inference result {inference_result_id} status to '{status}'")
            else:
                logger.warning(f"Inference result {inference_result_id} not found")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update processing status: {e}")
            raise
        finally:
            session.close()

    def parse_and_save_timing_data(self, inference_result):
        session = self.Session()
        try:
            data_json = json.loads(inference_result.data_json)
            race_data = data_json.get('race_data', [])

            if not race_data:
                logger.warning(f"No race_data in inference_result {inference_result.id}")
                return False

            table_type = inference_result.table_type
            lap_number = inference_result.lap_number

            for driver_entry in race_data:
                position = driver_entry.get('position')
                driver_code = driver_entry.get('driver')
                data_value = driver_entry.get('data')
                tire = driver_entry.get('tire')
                investigation = driver_entry.get('investigation', False)
                penalty = driver_entry.get('penalty', False)

                if not position or not driver_code:
                    logger.warning(f"Missing position or driver in entry: {driver_entry}")
                    continue

                is_in_pit = 1 if isinstance(data_value, str) and 'PIT' in data_value.upper() else 0
                is_out = 1 if isinstance(data_value, str) and data_value.upper() == 'OUT' else 0

                gap_to_leader = data_value if table_type == 'gap' else None
                interval = data_value if table_type == 'interval' else None
                tire_age = int(data_value) if table_type == 'tire_age' and str(data_value).isdigit() else None
                pitstop_count = int(data_value) if table_type == 'pitstops' and str(data_value).isdigit() else None

                record = RaceTimingData(
                    inference_result_id=inference_result.id,
                    timestamp=inference_result.timestamp,
                    year=inference_result.year,
                    race_number=inference_result.race_number,
                    circuit_name=inference_result.circuit_name,
                    race_id=inference_result.race_id,
                    lap_number=lap_number,
                    position=position,
                    driver_code=driver_code,
                    tire_compound=tire,
                    gap_to_leader=gap_to_leader,
                    interval=interval,
                    tire_age=tire_age,
                    pitstop_count=pitstop_count,
                    is_in_pit=is_in_pit,
                    is_out=is_out,
                    is_safety_car=inference_result.safety_car_status,
                    is_under_investigation=1 if investigation else 0,
                    has_penalty=1 if penalty else 0,
                    table_type=table_type
                )

                session.add(record)

            session.commit()
            logger.info(f"Parsed and saved timing data for inference_result {inference_result.id}")
            return True

        except json.JSONDecodeError as e:
            session.rollback()
            logger.error(f"Failed to parse JSON for inference_result {inference_result.id}: {e}")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to parse and save timing data: {e}")
            return False
        finally:
            session.close()

    def get_lap_summary(self, race_id, lap_number):
        session = self.Session()
        try:
            results = session.query(RaceTimingData).filter(
                RaceTimingData.race_id == race_id,
                RaceTimingData.lap_number == lap_number
            ).order_by(RaceTimingData.position).all()

            return results
        finally:
            session.close()

    def get_driver_race_progression(self, race_id, driver_code):
        session = self.Session()
        try:
            results = session.query(RaceTimingData).filter(
                RaceTimingData.race_id == race_id,
                RaceTimingData.driver_code == driver_code
            ).order_by(RaceTimingData.lap_number).all()

            return results
        finally:
            session.close()