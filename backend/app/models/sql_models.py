from sqlalchemy import Column, String, Float, Integer, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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

# --- New Application Tables ---

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    status = Column(String, default="DRAFT") # DRAFT, SUBMITTED, APPROVED, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vehicle_info = relationship("ApplicationVehicle", back_populates="application", uselist=False, cascade="all, delete-orphan")
    owner_info = relationship("ApplicationOwner", back_populates="application", uselist=False, cascade="all, delete-orphan")
    cargo_info = relationship("ApplicationCargo", back_populates="application", uselist=False, cascade="all, delete-orphan")
    transport_plan = relationship("ApplicationPlan", back_populates="application", uselist=False, cascade="all, delete-orphan")

class ApplicationVehicle(Base):
    __tablename__ = "application_vehicles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), unique=True)
    
    # Tractor
    tractor_plate_number = Column(String, nullable=True)
    tractor_model = Column(String, nullable=True)
    tractor_cur_weight = Column(Float, nullable=True)
    tractor_owner = Column(String, nullable=True)
    tractor_licence_image = Column(String, nullable=True) # Path or URL
    
    # Trailer
    trailer_plate_number = Column(String, nullable=True)
    trailer_model = Column(String, nullable=True)
    trailer_cur_weight = Column(Float, nullable=True)
    trailer_owner = Column(String, nullable=True)
    trailer_licence_image = Column(String, nullable=True)
    
    # Specs
    axle_count = Column(Integer, nullable=True)
    tire_count = Column(Integer, nullable=True)
    axis_weights = Column(JSON, nullable=True, default=list) # List[float] loads_ton
    axis_distances = Column(JSON, nullable=True, default=list) # List[float] spacings
    
    application = relationship("Application", back_populates="vehicle_info")

class ApplicationOwner(Base):
    __tablename__ = "application_owners"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), unique=True)
    
    # Entity
    entity_name = Column(String, nullable=True)
    entity_license_number = Column(String, nullable=True)
    entity_address = Column(String, nullable=True)
    entity_license_image = Column(String, nullable=True)
    
    # Driver/Handler
    driver_name = Column(String, nullable=True)
    driver_identity_number = Column(String, nullable=True)
    driver_telephone_number = Column(String, nullable=True)
    driver_identity_image = Column(String, nullable=True)
    
    application = relationship("Application", back_populates="owner_info")

class ApplicationCargo(Base):
    __tablename__ = "application_cargos"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), unique=True)
    
    cargo_name = Column(String, nullable=True)
    cargo_desc = Column(Text, nullable=True)
    cargo_weight = Column(Float, nullable=True)
    total_weight = Column(Float, nullable=True) # Important for Route Planning
    
    # Dimensions (Strings for now, e.g. "10,3,4")
    cargo_size_arr_str = Column(String, nullable=True)
    total_size_arr_str = Column(String, nullable=True) # Important for Route Planning
    
    outline_image = Column(String, nullable=True)
    
    application = relationship("Application", back_populates="cargo_info")

class ApplicationPlan(Base):
    __tablename__ = "application_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), unique=True)
    
    start_point = Column(String, nullable=True)
    end_point = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    application = relationship("Application", back_populates="transport_plan")
