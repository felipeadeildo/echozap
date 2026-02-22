from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from alexa.router import router as alexa_router
from database.engine import init_db
from scheduler.tasks import scheduler
from webhook.router import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:  # noqa: ARG001
    """Initialise the database and scheduler on startup; shut down on exit."""
    await init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="WhatsApp Brain", version="0.1.0", lifespan=lifespan)

app.include_router(alexa_router)
app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict:
    """Return a simple liveness check payload."""
    return {"status": "ok"}
