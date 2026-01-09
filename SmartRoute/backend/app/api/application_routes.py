from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.application_schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.services.application_service import ApplicationService

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(application: ApplicationCreate, db: Session = Depends(get_db)):
    return ApplicationService.create_application(db=db, application_in=application)

@router.get("/", response_model=List[ApplicationResponse])
def read_applications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return ApplicationService.get_applications(db=db, skip=skip, limit=limit)

@router.get("/{application_id}", response_model=ApplicationResponse)
def read_application(application_id: str, db: Session = Depends(get_db)):
    db_application = ApplicationService.get_application(db=db, application_id=application_id)
    if db_application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return db_application

@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(application_id: str, application: ApplicationUpdate, db: Session = Depends(get_db)):
    db_application = ApplicationService.update_application(db=db, application_id=application_id, application_in=application)
    if db_application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return db_application

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: str, db: Session = Depends(get_db)):
    success = ApplicationService.delete_application(db=db, application_id=application_id)
    if not success:
        raise HTTPException(status_code=404, detail="Application not found")
    return None
