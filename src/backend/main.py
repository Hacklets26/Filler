import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import developer, feed, project, swipe
from .storage import VIDEO_DIRECTORY

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GitTok API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(developer.router)
app.include_router(project.router)
app.include_router(swipe.router)
app.include_router(feed.router)
app.mount("/videos", StaticFiles(directory=VIDEO_DIRECTORY), name="videos")


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=30007)


if __name__ == "__main__":
    run()
