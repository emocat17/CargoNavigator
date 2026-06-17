from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Vehicle Schemas ---
class ApplicationVehicleBase(BaseModel):
    tractor_plate_number: Optional[str] = None
    tractor_model: Optional[str] = None
    tractor_cur_weight: Optional[float] = None
    tractor_owner: Optional[str] = None
    tractor_licence_image: Optional[str] = None
    
    trailer_plate_number: Optional[str] = None
    trailer_model: Optional[str] = None
    trailer_cur_weight: Optional[float] = None
    trailer_owner: Optional[str] = None
    trailer_licence_image: Optional[str] = None
    
    axle_count: Optional[int] = None
    tire_count: Optional[int] = None
    axis_weights: Optional[List[float]] = None
    axis_distances: Optional[List[float]] = None

class ApplicationVehicleCreate(ApplicationVehicleBase):
    pass

class ApplicationVehicle(ApplicationVehicleBase):
    id: str
    application_id: str

    class Config:
        from_attributes = True

# --- Owner Schemas ---
class ApplicationOwnerBase(BaseModel):
    entity_name: Optional[str] = None
    entity_license_number: Optional[str] = None
    entity_address: Optional[str] = None
    entity_license_image: Optional[str] = None
    
    driver_name: Optional[str] = None
    driver_identity_number: Optional[str] = None
    driver_telephone_number: Optional[str] = None
    driver_identity_image: Optional[str] = None

class ApplicationOwnerCreate(ApplicationOwnerBase):
    pass

class ApplicationOwner(ApplicationOwnerBase):
    id: str
    application_id: str

    class Config:
        from_attributes = True

# --- Cargo Schemas ---
class ApplicationCargoBase(BaseModel):
    cargo_name: Optional[str] = None
    cargo_desc: Optional[str] = None
    cargo_weight: Optional[float] = None
    total_weight: Optional[float] = None
    
    cargo_size_arr_str: Optional[str] = None
    total_size_arr_str: Optional[str] = None
    
    outline_image: Optional[str] = None

class ApplicationCargoCreate(ApplicationCargoBase):
    pass

class ApplicationCargo(ApplicationCargoBase):
    id: str
    application_id: str

    class Config:
        from_attributes = True

# --- Plan Schemas ---
class ApplicationPlanBase(BaseModel):
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ApplicationPlanCreate(ApplicationPlanBase):
    pass

class ApplicationPlan(ApplicationPlanBase):
    id: str
    application_id: str

    class Config:
        from_attributes = True

# --- Application Schemas ---
class ApplicationBase(BaseModel):
    status: Optional[str] = "DRAFT"

class ApplicationCreate(ApplicationBase):
    vehicle_info: Optional[ApplicationVehicleCreate] = None
    owner_info: Optional[ApplicationOwnerCreate] = None
    cargo_info: Optional[ApplicationCargoCreate] = None
    transport_plan: Optional[ApplicationPlanCreate] = None

class ApplicationUpdate(ApplicationBase):
    vehicle_info: Optional[ApplicationVehicleCreate] = None
    owner_info: Optional[ApplicationOwnerCreate] = None
    cargo_info: Optional[ApplicationCargoCreate] = None
    transport_plan: Optional[ApplicationPlanCreate] = None

class ApplicationResponse(ApplicationBase):
    id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    vehicle_info: Optional[ApplicationVehicle] = None
    owner_info: Optional[ApplicationOwner] = None
    cargo_info: Optional[ApplicationCargo] = None
    transport_plan: Optional[ApplicationPlan] = None

    class Config:
        from_attributes = True
