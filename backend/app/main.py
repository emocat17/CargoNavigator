from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.routes import router as api_router
from app.api.vehicle_routes import router as vehicle_router
from app.api.application_routes import router as application_router
from app.database import engine, Base
from app.models import sql_models # Import models to register them

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartRoute API", description="API for Smart Truck Route Planning")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:6789", # Frontend port
    "http://localhost:9876", # Backend port (for swagger)
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(api_router, prefix="/api/v1")
app.include_router(vehicle_router, prefix="/api/v1")
app.include_router(application_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "SmartRoute Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=9876, reload=True)
