from fastapi import FastAPI

from app.core.config import settings


app = FastAPI(title="EduReg Agent API", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "edureg-agent",
        "qdrant_url": settings.qdrant_url,
        "llm_provider": settings.llm_provider,
    }
