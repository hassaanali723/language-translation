from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Language Translator API",
    description="API for translating text between different languages",
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

# Import and include routers
from app.api.v1.endpoints import translation
app.include_router(translation.router, prefix="/api/v1", tags=["translation"])

@app.get("/")
async def root():
    return {"message": "Welcome to Language Translator API"} 