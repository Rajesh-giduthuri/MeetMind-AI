
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import init_db
from routers.auth import router as auth_router
from routers.meetings import router as meetings_router
from routers.qa import router as qa_router
from routers.summary import router as summary_router

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
SESSION_SECRET = os.getenv("SESSION_SECRET")

if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET is missing from environment variables")

SESSION_HTTPS_ONLY = (
    os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
    max_age=60 * 60 * 8,
)

# Initialize database
init_db()

# Public landing page
@app.get("/")
async def home():
    print("ROOT ROUTE: Serving index.html")
    print("FILE PATH:", FRONTEND_DIR / "index.html")
    return FileResponse(FRONTEND_DIR / "index.html")


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

