from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import translation

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for translating text, files, and documents between different languages",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    translation.router,
    prefix=settings.API_V1_STR,
    tags=["translation"]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Language Translator API",
        "docs_url": "/docs",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 