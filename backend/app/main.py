from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api import folders, files, jobs, database, snowflake
from backend.app.seeds.seed_streamlined import seed_platform
from backend.app.services.scheduler_service import SchedulerService

app = FastAPI(
    title="Enterprise CSV Data Ingestion and Workflow Automation Platform",
    description="CSV file upload, folder management, dynamic schema validation, MERGE upsert, and Snowflake warehouse integration",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the 3 primary sections + Snowflake config API
app.include_router(folders.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(database.router, prefix="/api")
app.include_router(snowflake.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    seed_platform()
    SchedulerService.start()

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Enterprise CSV Ingestion Platform",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
