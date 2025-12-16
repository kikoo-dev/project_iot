from sqlalchemy import create_engine, Column, Integer, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime


DATABASE_URL = "mysql+pymysql://root:@localhost/iot_project"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SensorReading(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float)
    gas_level = Column(Float)  # Dari MQ-135
    light_level = Column(Integer) # Dari LDR
    motion_detected = Column(Boolean) # Dari PIR
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Membuat tabel secara otomatis jika belum ada
Base.metadata.create_all(bind=engine)