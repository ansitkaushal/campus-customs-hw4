"""Campus Customs backend: catalogue, images, accounts, and the shopping chatbot.

Run from backend/:  uvicorn main:app --reload --port 8000

    /api/products...     catalogue + stock (this file)
    /api/auth/...        create account / log in / log out (auth.py)
    /api/chat            the PydanticAI shopping assistant (agent.py)
    /api/chat/stream     same, streamed as newline-delimited JSON events
    /images/...          product photos from data/products/
"""

import json
import logging
import re
import sqlite3
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded

from db import DATA_DIR, PROJECT_ROOT, get_db

# Load secrets before importing modules that read them: backend/.env, then
# hw4/.env, then any .env in a parent folder (e.g. a shared course .env).
# Earlier files win; nothing overrides variables already set in the shell.
for env_dir in (Path(__file__).resolve().parent, PROJECT_ROOT, *PROJECT_ROOT.resolve().parents):
    load_dotenv(env_dir / ".env", override=False)

import agent  # noqa: E402
import audit  # noqa: E402
import auth  # noqa: E402
from models import ChatHistoryMessage, ChatRequest, ChatResponse, ChatTurn, Customer, ShopDeps  # noqa: E402
from tools import category_of, current_product, image_url, product_cards, stock_by_product  # noqa: E402

log = logging.getLogger("campus_customs")
# Show our INFO logs (per-chat token/latency lines) next to Uvicorn's.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# Shown when the model provider's content filter blocks a message
# (e.g. jailbreak attempts), so the shopper gets an answer, not an error.
FILTERED_REPLY = (
    "Sorry, I can't help with that. I'm here for Campus Customs shopping: "
    "Yale apparel, sizes, prices, and stock. What can I help you find?"
)

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

# image_file_path in the DB is relative to data/ (e.g. "products/x.jpg");
# the "products/" part is stripped, so it's served at /images/x.jpg.
app.mount("/images", StaticFiles(directory=DATA_DIR / "products"), name="images")


def product_from_row(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "category": category_of(row["garment_type"]),
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "price": row["price"],
        "image_url": image_url(row["image_file_path"]),
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# --- Products -----------------------------------------------------------------


@app.get("/api/products")
def list_products() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock = stock_by_product(conn)
    products = []
    for r in rows:
        levels = stock.get(r["product_id"], [])
        products.append(
            {
                **product_from_row(r),
                "sizes_in_stock": [s.size for s in levels if s.quantity > 0],
                "low_stock_sizes": [s.size for s in levels if s.status == "low_stock"],
            }
        )
    return products


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock_rows = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    stock = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock_rows),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return {**product_from_row(row), "stock": stock}


# --- Chat -----------------------------------------------------------------------

HISTORY_TURNS = agent.MAX_HISTORY_TURNS  # past messages the agent sees each turn
SAFE_PATH = re.compile(r"/[A-Za-z0-9/_-]{0,199}")
UNAVAILABLE = "The shopping assistant is unavailable right now. Please try again in a moment."
LOOP_LIMIT_REPLY = (
    "Sorry, that one took me too many steps to look up. Could you ask about one product "
    "or one size at a time?"
)
UNVERIFIED_REPLY = (
    "Sorry, I couldn't double-check that price just now. The price on each product page "
    "comes straight from our catalogue. Want me to try again?"
)

# --- Rate limit: each shopper (or guest IP) gets RATE_LIMIT messages per RATE_WINDOW seconds.
# Stops a script or a stuck client from running up the model bill. In-memory, so it resets on restart.
RATE_LIMIT = 10
RATE_WINDOW = 60.0
_recent_messages: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str) -> None:
    now = time.monotonic()
    window = _recent_messages[key]
    while window and now - window[0] > RATE_WINDOW:
        window.popleft()
    if len(window) >= RATE_LIMIT:
        retry_in = int(RATE_WINDOW - (now - window[0])) + 1
        log.warning("Rate limit hit for %s", key)
        audit.log_event("rate_limited", who=key if key.startswith("user:") else "guest", stop_reason="rate_limited")
        raise HTTPException(
            429,
            f"You're sending messages a little fast. Please wait {retry_in} seconds and try again.",
            headers={"Retry-After": str(retry_in)},
        )
    window.append(now)


def load_customer(user: auth.UserOut) -> Customer:
    """The customer fields the agent is allowed to see (no password hash)."""
    with get_db() as conn:
        created = conn.execute("SELECT created_at FROM users WHERE id = ?", (user.id,)).fetchone()["created_at"]
    return Customer(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        member_since=(created or "")[:10],
    )


def load_history_turns(user_id: int, limit: int = HISTORY_TURNS) -> list[ChatTurn]:
    """The customer's most recent saved messages (oldest first), across all their visits."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        ChatTurn(
            role=r["role"],
            content=r["content"],
            product_ids=[p["product_id"] for p in json.loads(r["products_json"] or "[]") if "product_id" in p],
        )
        for r in reversed(rows)
    ]



def save_chat_turn(user_id: int, message: str, response: ChatResponse) -> None:
    """Store both sides of a turn in chat_messages so logged-in shoppers keep their history."""
    products_json = json.dumps([p.model_dump() for p in response.products])
    conn = get_db(readonly=False)
    try:
        with conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
                (user_id, message),
            )
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (user_id, response.reply, products_json),
            )
    finally:
        conn.close()


def prepare_chat(body: ChatRequest, request: Request) -> tuple[auth.UserOut | None, ShopDeps, list[ChatTurn]]:
    """Shared setup for both chat routes: rate limit, customer, page context, history."""
    user = auth.current_user(request)
    check_rate_limit(f"user:{user.id}" if user else f"ip:{request.client.host if request.client else '?'}")
    deps = ShopDeps(
        customer=load_customer(user) if user else None,
        current_product=current_product(body.page.product_id),
        # The path goes into the agent's instructions, so only plain URL paths are allowed.
        page_path=body.page.path if SAFE_PATH.fullmatch(body.page.path) else "/",
    )
    # Members: memory comes from the database (survives logout and new devices).
    # Guests: only what the browser sends from the current visit.
    history = load_history_turns(user.id) if user else body.history
    return user, deps, history


def fallback_reply(error: Exception) -> ChatResponse | None:
    """A shopper-friendly reply for errors that shouldn't look like an outage."""
    if isinstance(error, ModelHTTPError) and "content_filter" in str(error.body):
        log.warning("Chat message blocked by provider content filter")
        return ChatResponse(reply=FILTERED_REPLY)
    if isinstance(error, UsageLimitExceeded):  # agent hit LOOP_LIMITS
        log.warning("Agent hit loop limit: %s", error)
        return ChatResponse(reply=LOOP_LIMIT_REPLY)
    if isinstance(error, UnexpectedModelBehavior):  # e.g. price guard still failing after retries
        log.warning("Agent gave up after retries: %s", error)
        return ChatResponse(reply=UNVERIFIED_REPLY)
    return None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    user, deps, history = prepare_chat(body, request)
    try:
        response = await agent.chat(body.message.strip(), history, deps)
    except Exception as e:
        response = fallback_reply(e)
        if response is None:
            log.exception("Chat agent failed")
            raise HTTPException(502, UNAVAILABLE)

    if user:
        save_chat_turn(user.id, body.message.strip(), response)
    return response


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    """Like /api/chat, but streams newline-delimited JSON events so the reply appears as it's written.

    Events: status (a tool is running), reset (new answer attempt), delta (reply so far),
    done (final reply + product cards, same shape as /api/chat), error (message for the shopper).
    """
    user, deps, history = prepare_chat(body, request)  # rate limit errors return a normal 429
    message = body.message.strip()

    async def events():
        async for event in agent.chat_stream(message, history, deps):
            if event["type"] == "done":
                response = event["response"]
            elif event["type"] == "error":
                response = fallback_reply(event["error"])
                if response is None:
                    log.error("Chat agent failed", exc_info=event["error"])
                    yield json.dumps({"type": "error", "message": UNAVAILABLE}) + "\n"
                    return
            else:
                yield json.dumps(event) + "\n"
                continue
            if user:
                save_chat_turn(user.id, message, response)
            yield json.dumps({"type": "done", **response.model_dump()}) + "\n"
            return

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/chat/history", response_model=list[ChatHistoryMessage])
def chat_history(request: Request, limit: int = 30) -> list[ChatHistoryMessage]:
    """The logged-in shopper's most recent messages, oldest first. Guests get []."""
    user = auth.current_user(request)
    if user is None:
        return []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user.id, max(1, min(limit, 100))),
        ).fetchall()

    history = []
    for r in reversed(rows):
        # Rebuild cards from the database by id, so prices are always current.
        ids = [p["product_id"] for p in json.loads(r["products_json"] or "[]") if "product_id" in p]
        history.append(ChatHistoryMessage(role=r["role"], content=r["content"], products=product_cards(ids)))
    return history
