from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.db import models as _models
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="EduReg Agent API", version="0.1.0", lifespan=lifespan)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "edureg-agent",
        "qdrant_url": settings.qdrant_url,
        "llm_provider": settings.llm_provider,
    }
