from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.sql_models import VehicleProfile
from app.schemas.vehicle_schemas import VehicleProfileCreate, VehicleProfileResponse, VehicleProfileUpdate
from app.services.vehicle_classifier import classify_size, classify_axle_load, classify_combined
from app.services.space_checker import check_height, check_width, check_turning_radius, check_weight, full_space_check

router = APIRouter(prefix="/vehicles", tags=["Vehicle Profiles"])


# ── Request/Response models for classification and space checking ──

class ClassifyRequest(BaseModel):
    length: float = Field(..., gt=0, description="车长(米)")
    width: float = Field(..., gt=0, description="车宽(米)")
    height: float = Field(..., gt=0, description="车高(米)")
    total_weight: float = Field(..., gt=0, description="车货总重(吨)")
    axis_weight: float = Field(..., gt=0, description="最大轴重(吨)")
    axis_count: int = Field(..., gt=0, description="轴数")
    trailer_type: Optional[str] = Field("lowbed", description="挂车类型: lowbed 或 hydraulic")


class DimensionCheckRequest(BaseModel):
    length: float = Field(..., gt=0, description="车长(米)")
    width: float = Field(..., gt=0, description="车宽(米)")
    height: float = Field(..., gt=0, description="车高(米)")
    total_weight: float = Field(..., gt=0, description="车货总重(吨)")
    axis_weight: Optional[float] = Field(None, gt=0, description="最大轴重(吨)")
    axis_count: Optional[int] = Field(None, gt=0, description="轴数")

@router.post("/", response_model=VehicleProfileResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle_profile(vehicle: VehicleProfileCreate, db: Session = Depends(get_db)):
    # Validate logic: sum of axis weights should be close to total weight (optional warning, not blocking)
    # create model
    db_vehicle = VehicleProfile(**vehicle.model_dump())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@router.get("/", response_model=List[VehicleProfileResponse])
def read_vehicle_profiles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    profiles = db.query(VehicleProfile).offset(skip).limit(limit).all()
    return profiles

@router.get("/{vehicle_id}", response_model=VehicleProfileResponse)
def read_vehicle_profile(vehicle_id: str, db: Session = Depends(get_db)):
    vehicle = db.query(VehicleProfile).filter(VehicleProfile.id == vehicle_id).first()
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle profile not found")
    return vehicle

@router.put("/{vehicle_id}", response_model=VehicleProfileResponse)
def update_vehicle_profile(vehicle_id: str, vehicle_update: VehicleProfileUpdate, db: Session = Depends(get_db)):
    db_vehicle = db.query(VehicleProfile).filter(VehicleProfile.id == vehicle_id).first()
    if db_vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle profile not found")
    
    update_data = vehicle_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vehicle, key, value)
    
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_profile(vehicle_id: str, db: Session = Depends(get_db)):
    db_vehicle = db.query(VehicleProfile).filter(VehicleProfile.id == vehicle_id).first()
    if db_vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle profile not found")

    db.delete(db_vehicle)
    db.commit()
    return None


# ── Vehicle Classification & Space Passability Check ──

@router.post("/classify", tags=["Vehicle Classification"])
def classify_vehicle(request: ClassifyRequest):
    """Classify a vehicle by size and axle load per 《公路大件运输安全通行评价技术规范》.

    Returns size grade, axle load grade, and combined grade (worst of both).
    """
    vehicle_info = {
        "length": request.length,
        "width": request.width,
        "height": request.height,
        "total_weight": request.total_weight,
        "axis_weight": request.axis_weight,
        "axis_count": request.axis_count,
        "trailer_type": request.trailer_type,
    }
    result = classify_combined(vehicle_info)
    return result


@router.post("/check-dimensions", tags=["Vehicle Classification"])
def check_vehicle_dimensions(request: DimensionCheckRequest):
    """Comprehensive space passability check for a vehicle.

    Checks height clearance, lane width, turning radius, and bridge weight capacity
    against standard expressway design parameters.
    """
    vehicle_info = {
        "length": request.length,
        "width": request.width,
        "height": request.height,
        "total_weight": request.total_weight,
        "axis_weight": request.axis_weight,
        "axis_count": request.axis_count,
    }
    result = full_space_check(vehicle_info)
    return result
