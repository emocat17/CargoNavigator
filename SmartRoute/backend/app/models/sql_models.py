from sqlalchemy import Column, String, Float, Integer, JSON
from app.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class VehicleProfile(Base):
    __tablename__ = "vehicle_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True, nullable=False)
    license_plate = Column(String, nullable=True)
    
    # Basic Dimensions
    length = Column(Float, nullable=False) # meters
    width = Column(Float, nullable=False)  # meters
    height = Column(Float, nullable=False) # meters
    total_weight = Column(Float, nullable=False) # tons
    
    # Detailed Axle Info (Stored as JSON arrays)
    axis_count = Column(Integer, nullable=False, default=0)
    axis_weights = Column(JSON, nullable=False, default=list) # List[float]
    axis_distances = Column(JSON, nullable=False, default=list) # List[float]
    
    # Extended Info
    tire_count = Column(Integer, nullable=True)
    cargo_type = Column(String, nullable=True)
