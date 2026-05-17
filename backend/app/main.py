from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Investment Manager",
    description="Investment portfolio management and research platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
from app.api.errors import register_error_handlers  # noqa: E402
register_error_handlers(app)

# Register routers
from app.api import auth, stocks, portfolios, research, reports as report_routes, dashboard, simulation, broker_sync, snapshots, review  # noqa: E402
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(portfolios.router)
app.include_router(research.router)
app.include_router(report_routes.router)
app.include_router(dashboard.router)
app.include_router(simulation.router)
app.include_router(broker_sync.router)
app.include_router(snapshots.router)
app.include_router(review.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
