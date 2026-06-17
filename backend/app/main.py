from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.routes import router as api_router
from app.api.vehicle_routes import router as vehicle_router
from app.api.application_routes import router as application_router
from app.api.agent_routes import router as agent_router
from app.api.assessment_routes import router as assessment_router
from app.api.permit_routes import router as permit_router
from app.api.survey_routes import router as survey_router
from app.api.tracking_routes import router as tracking_router
from app.api.monitor_routes import router as monitor_router
from app.database import engine, Base
from app.models import sql_models  # Import models to register them
from app.models import chat_models  # Import chat models to register them for table creation
from app.models import tracking_models  # Import tracking models for table creation

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables and bridge DB."""
    Base.metadata.create_all(bind=engine)
    try:
        from app.bridge_db import init_bridge_db
        init_bridge_db()
        print("[Main] Bridge database initialized")
    except Exception as e:
        print(f"[Main] Bridge DB init skipped: {e}")
    yield


app = FastAPI(title="CargoNavigator API", description="大件运输智能选线系统 API", lifespan=lifespan)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:16789",
    "http://localhost:19876",
    "http://127.0.0.1:16789",
    "http://127.0.0.1:19876",
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
app.include_router(agent_router, prefix="/api/v1")
app.include_router(assessment_router, prefix="/api/v1")
app.include_router(permit_router, prefix="/api/v1")
app.include_router(survey_router, prefix="/api/v1")
app.include_router(tracking_router, prefix="/api/v1")
app.include_router(monitor_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    status = {
        "status": "ok",
        "service": "CargoNavigator Backend",
        "components": {},
    }

    # Bridge DB
    try:
        from app.bridge_db import query
        bridges = query("SELECT COUNT(*) as cnt FROM bridges")
        il = query("SELECT COUNT(*) as cnt FROM bridge_influence_lines")
        status["components"]["bridge_db"] = {
            "status": "ok",
            "bridges": bridges[0]["cnt"] if bridges else 0,
            "influence_lines": il[0]["cnt"] if il else 0,
        }
    except Exception as e:
        status["components"]["bridge_db"] = {"status": "error", "message": str(e)}

    # Spider data
    try:
        from pathlib import Path
        spider_dir = Path(__file__).resolve().parent.parent / "spider" / "data" / "road_details"
        const_count = len(list((spider_dir / "road_construction_details").glob("*.md"))) if spider_dir.exists() else 0
        inc_count = len(list((spider_dir / "traffic_incident_details").glob("*.md"))) if spider_dir.exists() else 0
        status["components"]["spider_data"] = {
            "status": "ok" if (const_count + inc_count) > 0 else "empty",
            "construction_events": const_count,
            "incident_events": inc_count,
        }
    except Exception as e:
        status["components"]["spider_data"] = {"status": "error", "message": str(e)}

    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=9876, reload=True)
