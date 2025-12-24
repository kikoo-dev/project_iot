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
    # Sensors used: DHT (temperature, humidity), LDR (light), PIR (motion)
    humidity = Column(Float, nullable=True)
    light_level = Column(Integer, nullable=False)
    ldr = Column(Float, nullable=True)
    motion_detected = Column(Boolean, nullable=False)
    motion_count = Column(Integer, nullable=True, default=0)
    # LED actuator states
    led_red = Column(Boolean, nullable=True, default=False)
    led_blue = Column(Boolean, nullable=True, default=False)
    led_yellow = Column(Boolean, nullable=True, default=False)
    led_white = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


Base.metadata.create_all(bind=engine)
