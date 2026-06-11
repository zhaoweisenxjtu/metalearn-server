"""FastAPI server for Meta-Learning Engine."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from engine.db.database import init_db

from .routers import users, tracks, nodes, reviews, assessments, journals, schedule, dashboard, knowledge, tools, admin
from .auth import require_auth


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Meta-Learning Engine API",
    version="0.1.0",
    description="认知科学驱动的元学习引擎 HTTP API",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


# Admin routes — no router-level auth (each endpoint uses verify_api_key directly for admin check)
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# All other routes require auth
app.include_router(users.router, prefix="/api/v1/users", tags=["users"], dependencies=[require_auth])
app.include_router(tracks.router, prefix="/api/v1/tracks", tags=["tracks"], dependencies=[require_auth])
app.include_router(nodes.router, prefix="/api/v1/nodes", tags=["nodes"], dependencies=[require_auth])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"], dependencies=[require_auth])
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"], dependencies=[require_auth])
app.include_router(journals.router, prefix="/api/v1/journals", tags=["journals"], dependencies=[require_auth])
app.include_router(schedule.router, prefix="/api/v1/schedule", tags=["schedule"], dependencies=[require_auth])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"], dependencies=[require_auth])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"], dependencies=[require_auth])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"], dependencies=[require_auth])


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
