import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import auth, developer, feed, project, swipe
from .storage import VIDEO_DIRECTORY

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FILLER API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # auth uses a bearer token, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (auth, developer, project, swipe, feed):
    app.include_router(module.router)
app.mount("/videos", StaticFiles(directory=VIDEO_DIRECTORY), name="videos")


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=30007)


if __name__ == "__main__":
    run()
