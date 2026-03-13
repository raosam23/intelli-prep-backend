from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import init_db
from contextlib import asynccontextmanager
from app.api.routes import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialze database
    await init_db()
    yield

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # change if required
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth.router,
    prefix='/api/auth',
    tags=['authentication']
)

@app.get("/health")
def get_health():
    return {"status": "ok"}