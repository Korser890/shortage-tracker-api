import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import health, overview, commodity

app = FastAPI(title="Global Resource Shortage Tracker API")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router,    prefix="/api")
app.include_router(overview.router,  prefix="/api")
app.include_router(commodity.router, prefix="/api")
