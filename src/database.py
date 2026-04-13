from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    Boolean,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()


class InferenceResult(Base):
    """Database model for storing inference results."""

    __tablename__ = "inference_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    year = Column(Integer, nullable=True)
    race_number = Column(Integer, nullable=True)
    circuit_name = Column(String(100), nullable=True)
    race_id = Column(Integer, nullable=True)

    lap_number = Column(Integer, nullable=True)
    conditions_air_temp = Column(Float, nullable=True)
    conditions_track_temp = Column(Float, nullable=True)
    wind = Column(Float, nullable=True)

    data_json = Column(Text, nullable=True)
    processing_status = Column(String(20), default="new")

    def __repr__(self):
        return f"<InferenceResult(id={self.id}, lap={self.lap_number}, race={self.race_number})>"


class RaceTimingData(Base):
    """Parsed and normalized race timing data."""

    __tablename__ = "race_timing_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inference_result_id = Column(Integer, nullable=False)

    timestamp = Column(DateTime, default=datetime.now)
    year = Column(Integer, nullable=True)
    race_number = Column(Integer, nullable=True)
    circuit_name = Column(String(100), nullable=True)
    race_id = Column(Integer, nullable=True)
    lap_number = Column(Integer, nullable=True)

    position = Column(Integer, nullable=False)
    driver_code = Column(String(50), nullable=False)
    position_delta = Column(Integer, nullable=True)

    gap = Column(String(20), nullable=True)
    in_pit = Column(Boolean, default=False)
    out_retired = Column(Boolean, default=False)

    interval = Column(String(20), nullable=True)
    last_lap = Column(String(20), nullable=True)

    current_tire = Column(String(1), nullable=True)
    tire_age = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<RaceTimingData(lap={self.lap_number}, pos={self.position}, driver={self.driver_code})>"


class DatabaseHandler:
    """Handles database connections and operations."""

    def __init__(self, config):
        self.config = config
        db_path = self.config.get("database.path", "data/f1_data.db")

        # If we need a fresh db as requested, we could drop the tables, but we will let user delete db file or drop tables.
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
            extractions = raw_results.get("extractions", {})
            if not extractions:
                return

            race_metadata = raw_results.get("race_metadata", {})
            key = next(iter(extractions))
            data = extractions[key]

            record = InferenceResult(
                timestamp=datetime.now(),
                year=race_metadata.get("year"),
                race_number=race_metadata.get("race_number"),
                circuit_name=race_metadata.get("circuit_name"),
                race_id=race_metadata.get("race_id"),
                lap_number=data.get("current_lap"),
                conditions_air_temp=data.get("conditions_air_temp"),
                conditions_track_temp=data.get("conditions_track_temp"),
                wind=data.get("wind"),
                data_json=json.dumps(data),
                processing_status="new",
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
            results = (
                session.query(InferenceResult)
                .filter(InferenceResult.processing_status == "new")
                .order_by(InferenceResult.timestamp.asc())
                .all()
            )

            logger.info(f"Found {len(results)} unprocessed inference results")
            return results
        finally:
            session.close()

    def update_processing_status(self, inference_result_id, status):
        session = self.Session()
        try:
            record = (
                session.query(InferenceResult)
                .filter(InferenceResult.id == inference_result_id)
                .first()
            )

            if record:
                record.processing_status = status
                session.commit()
                logger.info(
                    f"Updated inference result {inference_result_id} status to '{status}'"
                )
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
            race_data = data_json.get("race_data", [])

            if not race_data:
                logger.warning(
                    f"No race_data in inference_result {inference_result.id}"
                )
                return False

            lap_number = inference_result.lap_number

            for driver_entry in race_data:
                position = driver_entry.get("position")
                driver_code = driver_entry.get("driver_code")

                if not position or not driver_code:
                    logger.warning(
                        f"Missing position or driver in entry: {driver_entry}"
                    )
                    continue

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
                    position_delta=driver_entry.get("position_delta"),
                    gap=driver_entry.get("gap"),
                    in_pit=driver_entry.get("in_pit", False),
                    out_retired=driver_entry.get("out_retired", False),
                    interval=driver_entry.get("interval"),
                    last_lap=driver_entry.get("last_lap"),
                    current_tire=driver_entry.get("current_tire"),
                    tire_age=driver_entry.get("tire_age"),
                )

                session.add(record)

            session.commit()
            logger.info(
                f"Parsed and saved timing data for inference_result {inference_result.id}"
            )
            return True

        except json.JSONDecodeError as e:
            session.rollback()
            logger.error(
                f"Failed to parse JSON for inference_result {inference_result.id}: {e}"
            )
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
            results = (
                session.query(RaceTimingData)
                .filter(
                    RaceTimingData.race_id == race_id,
                    RaceTimingData.lap_number == lap_number,
                )
                .order_by(RaceTimingData.position)
                .all()
            )

            return results
        finally:
            session.close()

    def get_driver_race_progression(self, race_id, driver_code):
        session = self.Session()
        try:
            results = (
                session.query(RaceTimingData)
                .filter(
                    RaceTimingData.race_id == race_id,
                    RaceTimingData.driver_code == driver_code,
                )
                .order_by(RaceTimingData.lap_number)
                .all()
            )

            return results
        finally:
            session.close()
