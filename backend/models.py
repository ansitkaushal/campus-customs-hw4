"""Pydantic / PydanticAI structured types for the Campus Customs chatbot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

# --- Products ----------------------------------------------------------------


StockStatus = Literal["in_stock", "low_stock", "sold_out"]
LOW_STOCK_THRESHOLD = 3  # quantity at or below this counts as "low_stock"


class ProductCard(BaseModel):
    """What the website needs to draw a product card under a chat reply."""

    product_id: str
    name: str
    category: str = Field(description="Shopper-friendly group, e.g. Hoodies, Crewnecks.")
    garment_type: str
    description: str
    price: float
    image_url: str
    sizes_in_stock: list[str] = Field(default_factory=list, description="Sizes with quantity > 0.")
    low_stock_sizes: list[str] = Field(default_factory=list, description="Sizes with 1-3 left.")


class ProductSummary(BaseModel):
    """One search result: enough for the agent to pick and compare products."""

    product_id: str = Field(description="Exact id to pass to get_product_info / check_stock.")
    name: str
    category: str
    colors: list[str]
    price: float = Field(description="Price in US dollars, from the catalogue table.")
    sizes_in_stock: list[str] = Field(description="Sizes with quantity > 0.")


class SimilarProduct(BaseModel):
    """An in-stock alternative returned by find_similar_products."""

    product_id: str
    name: str
    category: str
    colors: list[str]
    price: float = Field(description="Price in US dollars, from the catalogue table.")
    sizes_in_stock: list[str]
    why_similar: str = Field(description="Short reason, e.g. 'same category; shares: hockey, navy'.")


class ProductInfo(BaseModel):
    """Description and price of one product, from the catalogue table (get_product_info)."""

    product_id: str
    name: str
    category: str
    garment_type: str = Field(description="Original style wording, e.g. 'quarter-zip pullover'.")
    description: str = Field(description="Catalogue description; quote or paraphrase it, don't embellish.")
    colors: list[str]
    price: float = Field(description="Price in US dollars. The only price you may quote.")


class SizeStock(BaseModel):
    """Stock for one size, from the inventory table."""

    size: str = Field(description="XS, S, M, L, XL, or XXL.")
    quantity: int = Field(description="Units on hand right now.")
    status: StockStatus = Field(
        description=f"sold_out if quantity is 0, low_stock if 1-{LOW_STOCK_THRESHOLD}, otherwise in_stock."
    )


class StockReport(BaseModel):
    """Stock for one product, either one requested size or every size (check_stock)."""

    product_id: str
    name: str
    requested_size: str | None = Field(description="The size asked about, or null when reporting all sizes.")
    sizes: list[SizeStock] = Field(description="Just the requested size, or all sizes XS to XXL.")
    sizes_in_stock: list[str] = Field(description="Every size of this product with quantity > 0.")
    sold_out_sizes: list[str] = Field(description="Every size of this product with quantity 0.")
    total_in_stock: int = Field(description="Units across all sizes.")


# --- Agent ---------------------------------------------------------------------


class Customer(BaseModel):
    """Who the agent is talking to. Built from the users table; never includes the password hash."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date, YYYY-MM-DD.")


class CurrentProduct(BaseModel):
    """The product page the shopper has open, verified against the catalogue."""

    product_id: str
    name: str


@dataclass
class ShopDeps:
    """Per-request context passed to the agent and its tools.

    customer is None for guests. current_product is None unless the shopper
    is on a product page. page_path is the website path they're on.
    """

    customer: Customer | None = None
    current_product: CurrentProduct | None = None
    page_path: str = "/"
    price_guard_trips: int = 0  # times the price fact-check rejected a reply this turn (for logs)


class CustomerProfile(BaseModel):
    """Returned by get_customer_profile: who the shopper is and what they've looked at before."""

    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = None
    past_messages: int = Field(0, description="Messages this customer has sent in earlier chats.")
    recently_viewed_in_chat: list[str] = Field(
        default_factory=list,
        description="Names (with product_id) of products shown to this customer in earlier chats, newest first.",
    )


MAX_PRODUCTS = 30  # covers the largest category (Crewnecks, 29 items)


class AgentReply(BaseModel):
    """The agent's structured output: chat text + the products to show."""

    reply: str = Field(description="Message to the shopper, in Campus Customs voice. Markdown allowed.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id of each product the reply mentions or recommends, most relevant first. "
        f"Only ids returned by tools. Empty if none. At most {MAX_PRODUCTS}.",
    )
    results_title: str | None = Field(
        default=None,
        description="Set when the shopper is browsing or searching for a type of item: a short heading for "
        "the results shown on the page, e.g. 'Hoodies' or 'Navy crewnecks under $60'. "
        "Null when the reply is about one specific product, or when no products are shown.",
    )


# --- Chat API ------------------------------------------------------------------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    product_ids: list[str] = Field(default_factory=list, max_length=MAX_PRODUCTS)


class PageContext(BaseModel):
    """Where the shopper is on the website when they send a message."""

    path: str = Field("/", max_length=200, description="e.g. /products/basic-hoodie-big-yale")
    product_id: str | None = Field(None, max_length=120, description="Set on a single-item page.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Used for guests only; logged-in history is loaded from the database.
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext = Field(default_factory=PageContext)


class ChatResponse(BaseModel):
    """API contract for POST /api/chat.

    `products` always appear as mini cards in the chat. When `results_title` is
    set, the website also shows them as a results grid on the Products page.
    """

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    results_title: str | None = None


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
