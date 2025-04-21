from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from postcast_rss.api.routers import podcasts
from postcast_rss.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RSS feed generator for IL Post podcasts",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(podcasts.router)


@app.get("/")
async def root():
    return {"message": "IL Post RSS Feed Generator", "docs": "/docs", "feeds": "/feeds"}
