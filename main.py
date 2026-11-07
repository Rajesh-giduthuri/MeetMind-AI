
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from database import init_db
from summary_service import generate_summary
from routers.auth import router as auth_router
from routers.meetings import router as meetings_router
from routers.qa import router as qa_router

from routers.summary import router as summary_router

load_dotenv()

app = FastAPI(
    title="MeetMind AI",
    description="Intelligent Meeting Summarization and Q&A",
    version="1.0.0",
)

# Register API routers
app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(qa_router)
app.include_router(summary_router)

# Frontend configuration
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)

# Browser navigation and authentication protection
class NavigationProtectionMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        path = request.url.path
        user_id = request.session.get("user_id")

        public_pages = {
            "/",
            "/auth",
            "/static/index.html",
            "/static/login.html",
        }

        protected_pages = {
            "/home",
            "/static/home.html",
            "/static/meetings.html",
            "/static/history.html",
            "/static/analysis.html",
            "/static/about.html",
            "/static/settings.html",
        }

        if path in public_pages and user_id:
            return RedirectResponse("/home", status_code=303)

        if path in protected_pages and not user_id:
            return RedirectResponse("/auth", status_code=303)

        response = await call_next(request)

        if path in protected_pages:
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

# Register navigation middleware first
app.add_middleware(NavigationProtectionMiddleware)

# Session configuration
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", ""),
    same_site="lax",
    https_only=False,  # Local development only
    max_age=60 * 60 * 8,  # 8-hour session
)


# Initialize database
init_db()

# Public landing page
@app.get("/")
async def home():
    print("ROOT ROUTE: Serving index.html")
    print("FILE PATH:", FRONTEND_DIR / "index.html")
    return FileResponse(FRONTEND_DIR / "index.html")

# # Public landing page
# @app.get("/")
# async def home():
#     return FileResponse(FRONTEND_DIR / "index.html")


# Authentication page
@app.get("/auth")
async def authentication():
    return FileResponse(FRONTEND_DIR / "login.html")


# User workspace
@app.get("/home")
async def workspace_home():
    return FileResponse(FRONTEND_DIR / "home.html")

# Health check
@app.get("/health")
def health():
    return {
        "status": "ok",
        "application": "MeetMind AI",
    }

