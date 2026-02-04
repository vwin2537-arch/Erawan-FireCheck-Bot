from sqlalchemy import Column, Integer, Float, String, Boolean, Date, Time, DateTime, func, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base
import datetime

class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    brightness = Column(Float)
    scan = Column(Float)
    track = Column(Float)
    acq_date = Column(Date, nullable=False)
    acq_time = Column(Time, nullable=False)
    satellite = Column(String, nullable=False)
    instrument = Column(String)
    confidence = Column(String)
    version = Column(String)
    bright_t31 = Column(Float)
    frp = Column(Float)
    daynight = Column(String)
    
    # Additional fields
    province = Column(String)
    district = Column(String)
    land_type = Column(String)
    
    # Metadata
    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('latitude', 'longitude', 'acq_date', 'acq_time', 'satellite', name='_hotspot_uc'),
    )

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, nullable=False)
    hotspot_count = Column(Integer, nullable=False)
    message_text = Column(String)
    sent_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="sent")
    error_message = Column(String)
    line_response = Column(String)

class CheckLog(Base):
    __tablename__ = "check_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checked_at = Column(DateTime, server_default=func.now())
    hotspots_found = Column(Integer, default=0)
    new_hotspots = Column(Integer, default=0)
    api_response_time_ms = Column(Integer)
    status = Column(String, default="success")
    error_message = Column(String)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
