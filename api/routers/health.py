from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from api.db import get_engine

router = APIRouter()

@router.get("/health")
def health_check():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "unreachable"}
        )
