from fastapi import FastAPI
from app.routes import articles, users

app = FastAPI(title="News Recommender")

app.include_router(articles.router, prefix="/articles")
app.include_router(users.router, prefix="/users")

@app.get("/")
def read_root():
    return {"message": "News Recommender API is running"}
