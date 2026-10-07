"""Create-account / login for Campus Customs.

Passwords are never stored: only a salted PBKDF2-SHA256 hash.
Sessions are an HMAC-signed, httpOnly cookie, so the browser's JavaScript
cannot read the token and the server cannot be tricked by an edited one.
"""

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# --- Password hashing -------------------------------------------------------

# New hashes: pbkdf2_sha256$<iterations>$<salt>$<hex digest>
# Seeded users use a 3-part format with no iteration count, which was made
# with 120,000 iterations (verified against the test user).
ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-SHA256
LEGACY_ITERATIONS = 120_000


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{ALGORITHM}${ITERATIONS}${salt}${_pbkdf2(password, salt, ITERATIONS)}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4:
        algo, iterations, salt, digest = parts
        iterations = int(iterations)
    elif len(parts) == 3:
        algo, salt, digest = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    if algo != ALGORITHM:
        return False
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), digest)


# Used when the email doesn't exist so a failed login takes the same time
# either way (prevents discovering which emails have accounts).
_DUMMY_HASH = hash_password(secrets.token_hex(8))

# --- Session cookie ---------------------------------------------------------

COOKIE_NAME = "cc_session"
SESSION_SECONDS = 7 * 24 * 3600
# Read from .env; if missing, a random per-process secret still works but
# everyone is logged out when the server restarts.
_SECRET = (os.environ.get("AUTH_SECRET") or secrets.token_hex(32)).encode()


def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_session_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_SECONDS}"
    token = f"{payload}.{_sign(payload)}"
    return base64.urlsafe_b64encode(token.encode()).decode()


def read_session_token(token: str) -> int | None:
    try:
        user_id, expires, signature = base64.urlsafe_b64decode(token.encode()).decode().split(".")
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(_sign(f"{user_id}.{expires}"), signature):
        return None
    if int(expires) < time.time():
        return None
    return int(user_id)


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        make_session_token(user_id),
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # set True when served over HTTPS
    )


# --- Request / response models ---------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    name: str
    email: str


def _user_out(row: sqlite3.Row) -> UserOut:
    # Older rows may only have `name`; fall back to splitting it.
    first, _, last = row["name"].partition(" ")
    return UserOut(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        name=row["name"],
        email=row["email"],
    )


def current_user(request: Request) -> UserOut | None:
    token = request.cookies.get(COOKIE_NAME)
    user_id = read_session_token(token) if token else None
    if user_id is None:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_out(row) if row else None


# --- Routes -----------------------------------------------------------------


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response) -> UserOut:
    email = body.email.strip().lower()
    first, last = body.first_name.strip(), body.last_name.strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    if not first or not last:
        raise HTTPException(422, "First and last name are required.")
    if body.password != body.confirm_password:
        raise HTTPException(422, "Passwords do not match.")

    conn = get_db(readonly=False)
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (name, first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", first, last, email, hash_password(body.password)),
            )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with that email already exists.")
    finally:
        conn.close()

    _set_session_cookie(response, row["id"])
    return _user_out(row)


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response) -> UserOut:
    email = body.email.strip().lower()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()

    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        # Same message for unknown email and wrong password.
        raise HTTPException(401, "Invalid email or password.")

    _set_session_cookie(response, row["id"])
    return _user_out(row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(request: Request) -> UserOut:
    user = current_user(request)
    if user is None:
        raise HTTPException(401, "Not logged in.")
    return user
