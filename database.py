from sqlalchemy import create_engine, Column, Integer, Float, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime

# Adjust DATABASE_URL if needed on your machine
DATABASE_URL = "mysql+pymysql://root:@localhost/iot_project"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class SensorReading(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    gas_level = Column(Float, nullable=False)
    light_level = Column(Integer, nullable=False)
    motion_detected = Column(Boolean, nullable=False)
    # Additional optional fields
    humidity = Column(Float, nullable=True)
    air_quality = Column(Float, nullable=True)
    distance = Column(Float, nullable=True)
    sound_level = Column(Float, nullable=True)
    mq135 = Column(Float, nullable=True)
    ldr = Column(Float, nullable=True)
    mic = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


Base.metadata.create_all(bind=engine)
