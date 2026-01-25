from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.sql_models import VehicleProfile
from app.schemas.vehicle_schemas import VehicleProfileCreate, VehicleProfileResponse, VehicleProfileUpdate

router = APIRouter(prefix="/vehicles", tags=["Vehicle Profiles"])

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
