from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, users

app = FastAPI(
    title="News Recommender Backend API",
    description="A swipe-based news application with ML-powered recommendations",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include user profile routes
app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/")
def read_root():
    return {
        "message": "News Recommender API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
