from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from alexa.router import router as alexa_router
from database.engine import init_db
from scheduler.tasks import scheduler
from webhook.router import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="WhatsApp Brain", version="0.1.0", lifespan=lifespan)

app.include_router(alexa_router)
app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
