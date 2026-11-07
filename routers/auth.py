from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import User
from auth_service import hash_password, verify_password

import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

import secrets
import string

oauth_config = Config(".env")

oauth = OAuth(oauth_config)

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)

oauth = OAuth(oauth_config)

oauth.register(
    name="google",
    client_id=oauth_config("GOOGLE_CLIENT_ID"),
    client_secret=oauth_config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


@router.post("/register")
def register_user(request: RegisterRequest):
    db = SessionLocal()

    try:
        existing_user = db.query(User).filter(
            (User.email == str(request.email).lower()) |
            (User.username == request.username.strip())
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email or username already registered.",
            )

        user = User(
            username=request.username.strip(),
            email=str(request.email).lower(),
            password_hash=hash_password(request.password),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "message": "Registration successful.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email or username already registered.",
        )

    finally:
        db.close()

@router.post("/login")
def login_user(request: LoginRequest, request_obj: Request):
    db = SessionLocal()

    try:
        login_input = str(request.email).strip()

        user = db.query(User).filter(
            (User.email == login_input.lower()) |
            (User.username == login_input)
        ).first()

        if not user or not verify_password(
            request.password, user.password_hash
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid username/email or password.",
            )

        request_obj.session["user_id"] = user.id

        return {
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }

    finally:
        db.close()

@router.get("/google")
async def google_login(request: Request, mode: str = "login"):
    if mode not in {"login", "register"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid Google authentication mode.",
        )

    if not oauth_config("GOOGLE_CLIENT_ID", default="") or not oauth_config(
        "GOOGLE_CLIENT_SECRET", default=""
    ):
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials are not configured.",
        )

    request.session["google_auth_mode"] = mode

    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.post("/logout")
def logout_user(request: Request):
    request.session.clear()

    return {"message": "Logout successful."}

@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    from starlette.responses import RedirectResponse

    db = SessionLocal()
    mode = request.session.pop("google_auth_mode", "login")

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            user_info = await oauth.google.userinfo(token=token)

        email = (user_info.get("email") or "").strip().lower()
        email_verified = user_info.get("email_verified", False)
        google_id = user_info.get("sub")

        if not email or email_verified is not True or not google_id:
            request.session.clear()
            return RedirectResponse(
                url="/?auth_error=unverified_google_email",
                status_code=303,
            )

        user = db.query(User).filter(User.email == email).first()

        if mode == "register":
            if user:
                request.session.clear()
                return RedirectResponse(
                    url="/?auth_error=account_exists",
                    status_code=303,
                )

            base_username = email.split("@")[0][:40] or "google_user"
            username = base_username

            while db.query(User).filter(
                User.username == username
            ).first():
                username = f"{base_username}_{secrets.token_hex(3)}"

            random_password = secrets.token_urlsafe(32)
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(random_password),
            )
            db.add(user)

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                request.session.clear()
                return RedirectResponse(
                    url="/?auth_error=account_exists",
                    status_code=303,
                )

            # Registration must not automatically log the user in.
            request.session.clear()
            return RedirectResponse(
                url="/?auth_success=google_registered",
                status_code=303,
            )

        # Login mode: only allow an existing account.
        if not user:
            request.session.clear()
            return RedirectResponse(
                url="/?auth_error=account_not_found",
                status_code=303,
            )

        request.session.clear()
        request.session["user_id"] = user.id

        return RedirectResponse(url="/home", status_code=303)

    except Exception as exc:
        request.session.clear()
        print(f"Google authentication failed: {exc}")
        return RedirectResponse(
            url="/?auth_error=google_auth_failed",
            status_code=303,
        )
    finally:
        db.close()

@router.get("/me")
def get_current_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not logged in.",
        )

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user:
            request.session.clear()
            raise HTTPException(
                status_code=401,
                detail="User account not found.",
            )

        return {
            "logged_in": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }

    finally:
        db.close()
