from sqlalchemy.orm import Session
from app.models.sql_models import (
    Application,
    ApplicationVehicle,
    ApplicationOwner,
    ApplicationCargo,
    ApplicationPlan
)
from app.schemas.application_schemas import ApplicationCreate, ApplicationUpdate

class ApplicationService:
    @staticmethod
    def get_application(db: Session, application_id: str):
        return db.query(Application).filter(Application.id == application_id).first()

    @staticmethod
    def get_applications(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Application).offset(skip).limit(limit).all()

    @staticmethod
    def create_application(db: Session, application_in: ApplicationCreate):
        # Create the main application record
        db_application = Application(status=application_in.status)
        db.add(db_application)
        db.flush() # Flush to get the ID
        
        # Create related records if provided
        if application_in.vehicle_info:
            vehicle_data = application_in.vehicle_info.dict(exclude_unset=True)
            db_vehicle = ApplicationVehicle(application_id=db_application.id, **vehicle_data)
            db.add(db_vehicle)
            
        if application_in.owner_info:
            owner_data = application_in.owner_info.dict(exclude_unset=True)
            db_owner = ApplicationOwner(application_id=db_application.id, **owner_data)
            db.add(db_owner)
            
        if application_in.cargo_info:
            cargo_data = application_in.cargo_info.dict(exclude_unset=True)
            db_cargo = ApplicationCargo(application_id=db_application.id, **cargo_data)
            db.add(db_cargo)
            
        if application_in.transport_plan:
            plan_data = application_in.transport_plan.dict(exclude_unset=True)
            db_plan = ApplicationPlan(application_id=db_application.id, **plan_data)
            db.add(db_plan)
            
        db.commit()
        db.refresh(db_application)
        return db_application

    @staticmethod
    def update_application(db: Session, application_id: str, application_in: ApplicationUpdate):
        db_application = db.query(Application).filter(Application.id == application_id).first()
        if not db_application:
            return None
            
        # Update main fields
        if application_in.status:
            db_application.status = application_in.status
            
        # Update or Create Vehicle Info
        if application_in.vehicle_info:
            vehicle_data = application_in.vehicle_info.dict(exclude_unset=True)
            if db_application.vehicle_info:
                for key, value in vehicle_data.items():
                    setattr(db_application.vehicle_info, key, value)
            else:
                db_vehicle = ApplicationVehicle(application_id=db_application.id, **vehicle_data)
                db.add(db_vehicle)

        # Update or Create Owner Info
        if application_in.owner_info:
            owner_data = application_in.owner_info.dict(exclude_unset=True)
            if db_application.owner_info:
                for key, value in owner_data.items():
                    setattr(db_application.owner_info, key, value)
            else:
                db_owner = ApplicationOwner(application_id=db_application.id, **owner_data)
                db.add(db_owner)

        # Update or Create Cargo Info
        if application_in.cargo_info:
            cargo_data = application_in.cargo_info.dict(exclude_unset=True)
            if db_application.cargo_info:
                for key, value in cargo_data.items():
                    setattr(db_application.cargo_info, key, value)
            else:
                db_cargo = ApplicationCargo(application_id=db_application.id, **cargo_data)
                db.add(db_cargo)

        # Update or Create Transport Plan
        if application_in.transport_plan:
            plan_data = application_in.transport_plan.dict(exclude_unset=True)
            if db_application.transport_plan:
                for key, value in plan_data.items():
                    setattr(db_application.transport_plan, key, value)
            else:
                db_plan = ApplicationPlan(application_id=db_application.id, **plan_data)
                db.add(db_plan)
        
        db.commit()
        db.refresh(db_application)
        return db_application

    @staticmethod
    def delete_application(db: Session, application_id: str):
        db_application = db.query(Application).filter(Application.id == application_id).first()
        if db_application:
            db.delete(db_application)
            db.commit()
            return True
        return False
