from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from api.routes import auth, users, articles, feed, search

app = FastAPI(
    title="News Recommender Backend API",
    description="""
    A swipe-based news application with ML-powered recommendations
    
    ## 🔐 Authentication Required
    
    Most endpoints require authentication. Follow these steps to test protected endpoints:
    
    ### Step 1: Get an Access Token
    1. Use `/auth/register` to create a new account, **OR**
    2. Use `/auth/login` to login with existing credentials
    3. Copy the `access_token` from the response
    
    ### Step 2: Authorize in Docs
    1. Click the 🔒 **Authorize** button at the top right of this page
    2. In the "BearerAuth" field, enter your token (no "Bearer" prefix needed)
    3. Click **Authorize**
    
    ### Step 3: Test Endpoints
    Now you can test all protected endpoints! The token will be automatically included.
    
    ---
    
    ## 🚀 Quick Start
    
    **For new users:** Try `/auth/register` first  
    **For existing users:** Try `/auth/login` first  
    **Then:** Use the token to access `/articles`, `/users/profile`, `/feed/personalized`, etc.
    """,
    version="1.0.0"
)

# Configure OpenAPI security for docs authentication
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT access token (without 'Bearer' prefix)"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS disabled for development
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure properly for production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Include authentication routes
app.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Include user profile routes
app.include_router(users.router, prefix="/users", tags=["users"])

# Include article content management routes
app.include_router(articles.router, prefix="/articles", tags=["articles"])

# Include feed routes
app.include_router(feed.router, prefix="/feed", tags=["feed"])

# Include search routes
app.include_router(search.router, prefix="/search", tags=["search"])

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

@app.get("/demo")
def serve_demo_frontend():
    """Serve the demo frontend HTML file"""
    return FileResponse("demo-frontend.html")

@app.get("/view-tracking-demo")
def serve_view_tracking_demo():
    """Serve the view tracking demo HTML file"""
    return FileResponse("view_tracking_demo.html")
