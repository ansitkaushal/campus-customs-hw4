"""Tools the Campus Customs agent can call.

Every price and stock number the agent gives comes from these functions, which
read the SQLite database directly (read-only).
"""

from __future__ import annotations

import difflib
import json
import math
import re
import sqlite3

from pydantic_ai import ModelRetry, RunContext

from db import get_db
from models import (
    LOW_STOCK_THRESHOLD,
    CurrentProduct,
    CustomerProfile,
    ShopDeps,
    SimilarProduct,
    MAX_PRODUCTS,
    ProductCard,
    ProductInfo,
    ProductSummary,
    SizeStock,
    StockReport,
    StockStatus,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
CATEGORIES = ["T-Shirts", "Long Sleeves", "Crewnecks", "Hoodies", "Quarter-Zips", "Jackets & Fleece"]

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "on", "to", "do", "you", "have", "any",
    "some", "something", "i", "me", "my", "want", "need", "looking", "show", "find", "is", "are",
    "yale", "campus", "customs", "merch", "gear", "item", "items", "shirt", "please", "that", "it",
}
SYNONYMS = {"tee": "t-shirt", "tees": "t-shirt", "sweatshirt": "crewneck", "hoody": "hoodie", "hooded": "hoodie",
            "1/4": "quarter-zip", "quarterzip": "quarter-zip", "grey": "gray"}


def category_of(garment_type: str) -> str:
    """Collapse the catalogue's 22 raw garment types into 6 groups (matches the website)."""
    t = garment_type.lower()
    if "quarter-zip" in t:
        return "Quarter-Zips"
    if "hood" in t:
        return "Hoodies"
    if "jacket" in t or "full-zip" in t:
        return "Jackets & Fleece"
    if "crewneck" in t or "mockneck" in t:
        return "Crewnecks"
    if "long-sleeve" in t:
        return "Long Sleeves"
    return "T-Shirts"


def image_url(image_file_path: str) -> str:
    return "/images/" + image_file_path.removeprefix("products/")


SIZE_ALIASES = {
    "EXTRA SMALL": "XS", "X-SMALL": "XS", "SMALL": "S", "MEDIUM": "M", "MED": "M", "LARGE": "L",
    "EXTRA LARGE": "XL", "X-LARGE": "XL", "2XL": "XXL", "XX-LARGE": "XXL", "2X": "XXL",
}


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    if quantity <= LOW_STOCK_THRESHOLD:
        return "low_stock"
    return "in_stock"


def _stock_rows(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    levels = [SizeStock(size=r["size"], quantity=r["quantity"], status=stock_status(r["quantity"])) for r in rows]
    return sorted(levels, key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)


def _normalize_size(size: str) -> str:
    """Map "medium", "2xl", "l" etc. to one of the six database sizes."""
    s = size.strip().upper()
    s = SIZE_ALIASES.get(s, s)
    if s not in SIZE_ORDER:
        raise ModelRetry(f"Unknown size {size!r}. We stock: {', '.join(SIZE_ORDER)}.")
    return s


def _unknown_product(conn: sqlite3.Connection, product_id: str) -> ModelRetry:
    """Error for a bad id, with close matches so the agent can correct itself."""
    ids = [r["product_id"] for r in conn.execute("SELECT product_id FROM catalogue")]
    close = difflib.get_close_matches(product_id, ids, n=3, cutoff=0.5)
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    return ModelRetry(f"No product with id {product_id!r}.{hint} Use search_products to find the exact id.")


def _words(text: str) -> set[str]:
    """Whole words, keeping hyphenated ones intact ("short-sleeve" is not "short")."""
    return set(re.findall(r"[a-z0-9/'-]+", text.lower()))


def _terms(query: str) -> list[str]:
    out = []
    for w in _words(query):
        w = SYNONYMS.get(w, w)
        if w not in STOPWORDS and len(w) >= 2:
            out.append(w)
    return out


def _hit(term: str, words: set[str]) -> bool:
    # Match singular or plural: "hoodies" finds "hoodie", "college" finds "colleges".
    return term in words or term.rstrip("s") in words or f"{term}s" in words


def _score(row: sqlite3.Row, terms: list[str]) -> int:
    name = _words(row["name"])
    tags = _words(" ".join(json.loads(row["search_tags"])))
    colors = _words(" ".join(json.loads(row["colors"])))
    kind = _words(f"{row['garment_type']} {category_of(row['garment_type'])}")
    desc = _words(row["description"])
    score = 0
    for t in terms:
        score += 4 * _hit(t, name) + 2 * _hit(t, tags) + 2 * _hit(t, colors) + 2 * _hit(t, kind) + _hit(t, desc)
    return score


# --- Agent tools ---------------------------------------------------------------


def search_products(
    query: str = "",
    category: str | None = None,
    max_price: float | None = None,
    limit: int = 12,
) -> list[ProductSummary]:
    """Search the Campus Customs catalogue.

    Args:
        query: Keywords such as style, color, college, sport, school, or family word
            (e.g. "navy", "Davenport", "hockey", "Yale Mom"). Leave empty and set `category`
            to list a whole type of item (e.g. every hoodie).
        category: Optional filter, one of: T-Shirts, Long Sleeves, Crewnecks, Hoodies,
            Quarter-Zips, Jackets & Fleece.
        max_price: Optional maximum price in dollars.
        limit: Maximum number of results (1-30). Use a higher limit when the shopper wants to browse.
    """
    if category and category not in CATEGORIES:
        raise ModelRetry(f"Unknown category {category!r}. Use one of: {', '.join(CATEGORIES)}.")
    limit = max(1, min(limit, MAX_PRODUCTS))
    terms = _terms(query)

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        scored = []
        for row in rows:
            if category and category_of(row["garment_type"]) != category:
                continue
            if max_price is not None and row["price"] > max_price:
                continue
            score = _score(row, terms) if terms else 1
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))

        results = []
        for _, row in scored[:limit]:
            stock = _stock_rows(conn, row["product_id"])
            results.append(
                ProductSummary(
                    product_id=row["product_id"],
                    name=row["name"],
                    category=category_of(row["garment_type"]),
                    colors=json.loads(row["colors"]),
                    price=row["price"],
                    sizes_in_stock=[s.size for s in stock if s.quantity > 0],
                )
            )
    return results


def get_product_info(product_id: str) -> ProductInfo:
    """Get the description, colors, and price of one product from the catalogue.

    Use for "tell me about…", "what does it look like?", and "how much is…?" questions.

    Args:
        product_id: The exact product_id from search_products (e.g. "basic-hoodie-big-yale").
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise _unknown_product(conn, product_id)
    return ProductInfo(
        product_id=row["product_id"],
        name=row["name"],
        category=category_of(row["garment_type"]),
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
    )


def check_stock(product_id: str, size: str | None = None) -> StockReport:
    """Check how many of one product are in stock, from the inventory table.

    Use for any availability question. Pass `size` when the shopper names a size;
    leave it empty to get every size.

    Args:
        product_id: The exact product_id from search_products.
        size: Optional size: XS, S, M, L, XL, or XXL (words like "medium" or "2XL" also work).
    """
    requested = _normalize_size(size) if size and size.strip() else None

    with get_db() as conn:
        row = conn.execute("SELECT name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise _unknown_product(conn, product_id)
        levels = _stock_rows(conn, product_id)

    return StockReport(
        product_id=product_id,
        name=row["name"],
        requested_size=requested,
        sizes=[s for s in levels if s.size == requested] if requested else levels,
        sizes_in_stock=[s.size for s in levels if s.quantity > 0],
        sold_out_sizes=[s.size for s in levels if s.quantity == 0],
        total_in_stock=sum(s.quantity for s in levels),
    )


def find_similar_products(
    product_id: str,
    size: str | None = None,
    color: str | None = None,
    limit: int = 4,
) -> list[SimilarProduct]:
    """Find in-stock alternatives to one product, e.g. when it's sold out in the shopper's size.

    Returns products from the same category, ranked by how much they have in common
    (shared tags, colors, and name words), that are in stock in `size` (if given) and
    come in `color` (if given). Never returns the original product.

    Args:
        product_id: The product to find alternatives for.
        size: Optional size the alternative must be in stock in (XS, S, M, L, XL, XXL).
        color: Optional color the alternative should come in (e.g. "gray", "white").
        limit: Maximum number of alternatives (1-8).
    """
    wanted_size = _normalize_size(size) if size and size.strip() else None
    wanted_color = color.strip().lower() if color and color.strip() else None
    limit = max(1, min(limit, 8))

    with get_db() as conn:
        base = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if base is None:
            raise _unknown_product(conn, product_id)
        base_cat = category_of(base["garment_type"])
        rows = conn.execute("SELECT * FROM catalogue").fetchall()

        def words_of(row: sqlite3.Row) -> set[str]:
            return (
                _words(" ".join(json.loads(row["search_tags"])))
                | _words(" ".join(json.loads(row["colors"])))
                | _words(row["name"])
            ) - STOPWORDS

        # Rare shared words ("hockey", "davenport") count far more than common ones
        # ("college", "hoodie"), so the closest themes rank first.
        row_words = {r["product_id"]: words_of(r) for r in rows}
        doc_freq: dict[str, int] = {}
        for ws in row_words.values():
            for w in ws:
                doc_freq[w] = doc_freq.get(w, 0) + 1
        n = len(rows)
        base_words = row_words[product_id]

        candidates = []
        for row in rows:
            if row["product_id"] == product_id or category_of(row["garment_type"]) != base_cat:
                continue
            colors = json.loads(row["colors"])
            if wanted_color and not any(wanted_color in c.lower() for c in colors):
                continue
            stock = _stock_rows(conn, row["product_id"])
            in_stock = [s.size for s in stock if s.quantity > 0]
            if not in_stock or (wanted_size and wanted_size not in in_stock):
                continue
            shared = sorted(base_words & row_words[row["product_id"]], key=lambda w: doc_freq[w])
            score = sum(math.log(n / doc_freq[w]) for w in shared)
            candidates.append((score, row, colors, in_stock, shared))

    candidates.sort(key=lambda c: (-c[0], abs(c[1]["price"] - base["price"]), c[1]["name"]))
    return [
        SimilarProduct(
            product_id=row["product_id"],
            name=row["name"],
            category=base_cat,
            colors=colors,
            price=row["price"],
            sizes_in_stock=in_stock,
            why_similar=f"same category ({base_cat})" + (f"; shares: {', '.join(shared[:3])}" if shared else ""),
        )
        for _, row, colors, in_stock, shared in candidates[:limit]
    ]


def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerProfile:
    """Get the logged-in shopper's profile and the products shown to them in earlier chats.

    Use when the shopper asks about their account details ("what email am I using?") or
    refers to past visits ("that hoodie you showed me last time"). Guests get logged_in=false.
    """
    customer = ctx.deps.customer
    if customer is None:
        return CustomerProfile(logged_in=False)

    with get_db() as conn:
        past = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = ? AND role = 'user'", (customer.user_id,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT products_json FROM chat_messages WHERE user_id = ? AND role = 'assistant' "
            "AND products_json IS NOT NULL ORDER BY id DESC LIMIT 50",
            (customer.user_id,),
        ).fetchall()

    seen: dict[str, str] = {}
    for r in rows:
        for p in json.loads(r["products_json"] or "[]"):
            if "product_id" in p and p["product_id"] not in seen:
                seen[p["product_id"]] = p.get("name", p["product_id"])
    return CustomerProfile(
        logged_in=True,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        member_since=customer.member_since,
        past_messages=past,
        recently_viewed_in_chat=[f"{name} ({pid})" for pid, name in list(seen.items())[:10]],
    )


AGENT_TOOLS = [search_products, get_product_info, check_stock, find_similar_products, get_customer_profile]


# --- Helpers for the API (not agent tools) -------------------------------------


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Turn agent-chosen ids into cards built from the database, in the same order.

    Unknown ids are dropped, so the agent can never put a made-up product
    or price on the page.
    """
    ids = list(dict.fromkeys(product_ids))  # dedupe, keep order
    if not ids:
        return []
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM catalogue WHERE product_id IN ({','.join('?' * len(ids))})", ids
        ).fetchall()
        stock = stock_by_product(conn, ids)
    by_id = {r["product_id"]: r for r in rows}
    return [card_from_row(r, stock.get(pid, [])) for pid in ids if (r := by_id.get(pid)) is not None]


def stock_by_product(conn: sqlite3.Connection, product_ids: list[str] | None = None) -> dict[str, list[SizeStock]]:
    """Stock rows grouped by product, sizes in XS→XXL order (all products if ids is None)."""
    if product_ids is None:
        rows = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    else:
        rows = conn.execute(
            f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({','.join('?' * len(product_ids))})",
            product_ids,
        ).fetchall()
    out: dict[str, list[SizeStock]] = {}
    for r in rows:
        out.setdefault(r["product_id"], []).append(
            SizeStock(size=r["size"], quantity=r["quantity"], status=stock_status(r["quantity"]))
        )
    for levels in out.values():
        levels.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)
    return out


def card_from_row(r: sqlite3.Row, stock: list[SizeStock]) -> ProductCard:
    return ProductCard(
        product_id=r["product_id"],
        name=r["name"],
        category=category_of(r["garment_type"]),
        garment_type=r["garment_type"],
        description=r["description"],
        price=r["price"],
        image_url=image_url(r["image_file_path"]),
        sizes_in_stock=[s.size for s in stock if s.quantity > 0],
        low_stock_sizes=[s.size for s in stock if s.status == "low_stock"],
    )


def current_product(product_id: str | None) -> CurrentProduct | None:
    """Validate the product id the website says the shopper is viewing.

    Only real catalogue ids are passed to the agent, so this field can't be
    used to slip arbitrary text into the prompt.
    """
    if not product_id:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT product_id, name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    return CurrentProduct(product_id=row["product_id"], name=row["name"]) if row else None
