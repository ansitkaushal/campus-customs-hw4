"""Campus Customs agent: wiring for the PydanticAI shopping assistant.

    prompts/prompt.md  -> system prompt (voice + safety rules)
    tools.py           -> search_products, get_product_info, check_stock,
                          find_similar_products, get_customer_profile
    models.py          -> AgentReply (structured output), ShopDeps (customer + page context)

The model is reached through Portkey's OpenAI-compatible endpoint using
PORTKEY_API_KEY from .env. Set CHAT_MODEL in .env to try another model.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from collections.abc import AsyncIterable, AsyncIterator
from functools import lru_cache
from itertools import combinations_with_replacement
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    AgentStreamEvent,
    FunctionToolCallEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    ToolCallPart,
    ToolCallPartDelta,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from pydantic_core import from_json

import audit
from models import MAX_PRODUCTS, AgentReply, ChatResponse, ChatTurn, ShopDeps
from tools import AGENT_TOOLS, product_cards

log = logging.getLogger("campus_customs.agent")

HERE = Path(__file__).resolve().parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"

DEFAULT_MODEL = "gpt-5.6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MAX_HISTORY_TURNS = 12  # past messages sent to the model each turn (cost vs. memory)
MAX_HISTORY_CHARS = 700  # long old replies are trimmed; the product ids note is kept
OUTPUT_TOOL = "final_result"  # PydanticAI's name for the structured-output tool

# Loop limits: a normal answer takes 2-5 model requests and 1-4 tool calls.
# These caps stop a confused agent from looping (and running up cost) forever.
LOOP_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=12)

# Shown in the chat while a tool runs (streaming only).
TOOL_STATUS = {
    "search_products": "Searching the catalogue…",
    "get_product_info": "Looking up product details…",
    "check_stock": "Checking stock…",
    "find_similar_products": "Finding similar items in stock…",
    "get_customer_profile": "Checking your account…",
}


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def build_agent() -> Agent[ShopDeps, AgentReply]:
    """Create the agent once (on first chat) and reuse it for every request."""
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to the .env file.")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-provider": "openai"},
    )
    model = OpenAIChatModel(
        os.environ.get("CHAT_MODEL", DEFAULT_MODEL),
        provider=OpenAIProvider(openai_client=client),
    )

    agent = Agent(
        model,
        deps_type=ShopDeps,
        output_type=AgentReply,
        system_prompt=load_system_prompt(),
        tools=AGENT_TOOLS,
        retries=2,
    )

    @agent.instructions
    def shopper_context(ctx: RunContext[ShopDeps]) -> str:
        return context_instructions(ctx.deps)

    @agent.output_validator
    def price_guard(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
        return check_prices(ctx, output)

    return agent


# --- Price fact-check guard -----------------------------------------------------

PRICE_IN_TEXT = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
PRICE_IN_TOOL = re.compile(r'"price"\s*:\s*(\d+(?:\.\d+)?)')


def tool_prices(messages: list[ModelMessage]) -> set[float]:
    """Every price that a tool returned during this run."""
    prices: set[float] = set()
    for m in messages:
        if isinstance(m, ModelRequest):
            for part in m.parts:
                if isinstance(part, ToolReturnPart):
                    prices.update(float(x) for x in PRICE_IN_TOOL.findall(part.model_response_str()))
    return prices


def allowed_amounts(prices: set[float], prompt: str) -> set[float]:
    """Tool prices, totals of up to 3 items, and amounts the shopper typed (e.g. "under $60")."""
    allowed = {round(sum(combo), 2) for n in (1, 2, 3) for combo in combinations_with_replacement(prices, n)}
    allowed.update(float(x.replace(",", "")) for x in PRICE_IN_TEXT.findall(prompt))
    return allowed


def check_prices(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
    """Reject replies that quote a dollar amount no tool returned this turn.

    The prompt already says "never make up prices"; this enforces it in code.
    Raising ModelRetry sends the message back to the model, which must look the
    price up (or drop it) and answer again.
    """
    if ctx.partial_output:  # streaming snapshots: only check the finished reply
        return output
    quoted = {float(x.replace(",", "")) for x in PRICE_IN_TEXT.findall(output.reply)}
    if not quoted:
        return output
    prompt = ctx.prompt if isinstance(ctx.prompt, str) else ""
    allowed = allowed_amounts(tool_prices(ctx.messages), prompt)
    unverified = sorted(q for q in quoted if not any(abs(q - a) < 0.005 for a in allowed))
    if unverified:
        ctx.deps.price_guard_trips += 1
        amounts = ", ".join(f"${q:.2f}" for q in unverified)
        log.warning("Price guard rejected reply quoting %s", amounts)
        raise ModelRetry(
            f"Your reply mentions {amounts}, but no tool returned that price in this turn. "
            "Call get_product_info or search_products for every product whose price you mention "
            "and quote those prices exactly, or remove the price from your reply."
        )
    return output


# --- Context and history ------------------------------------------------------


def context_instructions(deps: ShopDeps) -> str:
    """Per-request facts added to the system prompt: who is chatting and what page they're on."""
    lines = ["## Current context"]
    c = deps.customer
    if c:
        lines.append(
            f"- Customer: logged in as **{c.first_name} {c.last_name}** ({c.email}), member since {c.member_since}. "
            "Their past chat with you is included above, so you can refer back to it."
        )
    else:
        lines.append("- Customer: a guest (not logged in). Their chat won't be saved after they leave.")

    p = deps.current_product
    if p:
        lines.append(
            f"- Page: the shopper is viewing the product page for **{p.name}** (product_id `{p.product_id}`). "
            "If they say \"this\", \"it\", or \"this one\" without naming a product, they mean this product, "
            "even if a different product was discussed earlier in the chat. "
            "Use this product_id directly with get_product_info / check_stock."
        )
    else:
        lines.append(f"- Page: the shopper is on `{deps.page_path}` (not a product page).")
    return "\n".join(lines)


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Convert past chat turns into PydanticAI messages.

    Assistant turns get a note listing the products that were shown, so the agent
    can resolve "the second one" or "that hoodie" in later messages.
    """
    messages: list[ModelMessage] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            content = turn.content
            if len(content) > MAX_HISTORY_CHARS:
                content = content[:MAX_HISTORY_CHARS].rstrip() + " …"
            if turn.product_ids:
                content += f"\n\n[Products shown with this reply: {', '.join(turn.product_ids)}]"
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


def with_page_note(message: str, deps: ShopDeps) -> str:
    """Attach the product page to the shopper's message itself.

    Saying it only in the system instructions wasn't enough: with a long saved
    history, the model kept resolving "this" to a product from earlier in the
    chat. Next to the question, the page wins. Only the raw message is saved.
    """
    p = deps.current_product
    if p is None:
        return message
    return f"[Page context: I'm on the product page for {p.name} (product_id {p.product_id}).]\n{message}"


def finish(output: AgentReply) -> ChatResponse:
    """Turn the agent's output into the API response, with cards built from the database."""
    products = product_cards(output.product_ids[:MAX_PRODUCTS])
    # No page results without products (e.g. nothing matched).
    title = (output.results_title or "").strip() or None
    return ChatResponse(reply=output.reply, products=products, results_title=title if products else None)


def log_usage(result, deps: ShopDeps, started: float, mode: str) -> None:
    u = result.usage  # RunUsage (a property in pydantic-ai v2)
    log.info(
        "chat %s | %s | %.1fs | requests=%d tool_calls=%d | tokens in=%d (cached %d) out=%d | cost=$%s | "
        "price_guard_trips=%d",
        mode,
        f"user={deps.customer.user_id}" if deps.customer else "guest",
        time.perf_counter() - started,
        u.requests,
        u.tool_calls,
        u.input_tokens,
        u.cache_read_tokens,
        u.output_tokens,
        f"{u.cost:.5f}" if u.cost is not None else "?",
        deps.price_guard_trips,
    )


def stop_reason_for(error: BaseException) -> str:
    """Short label for why a run ended without an answer (used in the audit trail)."""
    if isinstance(error, UsageLimitExceeded):
        return "loop_limit"
    if isinstance(error, ModelHTTPError) and "content_filter" in str(error.body):
        return "content_filter"
    if isinstance(error, UnexpectedModelBehavior):
        return "retries_exhausted"
    if isinstance(error, asyncio.CancelledError):
        return "cancelled"
    return f"error:{type(error).__name__}"


async def run_agent(message: str, history: list[ChatTurn], deps: ShopDeps, mode: str, event_stream_handler=None):
    """Run the agent once, with loop limits, and write the run to the audit trail.

    Shared by the JSON and streaming routes. Re-raises errors after logging them.
    """
    run_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc)
    who = f"user:{deps.customer.user_id}" if deps.customer else "guest"
    page = deps.current_product.product_id if deps.current_product else deps.page_path
    with capture_run_messages() as messages:
        try:
            result = await build_agent().run(
                with_page_note(message, deps),
                deps=deps,
                message_history=to_message_history(history),
                usage_limits=LOOP_LIMITS,
                event_stream_handler=event_stream_handler,
            )
        except BaseException as e:
            new = messages[len(to_message_history(history)) :]  # drop the replayed history
            audit.append(
                audit.run_entries(
                    run_id, new, who=who, page=page, message=message, mode=mode, started_at=started_at,
                    stop_reason=stop_reason_for(e), duration_s=time.perf_counter() - started,
                    extra={"price_guard_trips": deps.price_guard_trips},
                )
            )
            raise
    log_usage(result, deps, started, mode)
    output = result.output
    audit.append(
        audit.run_entries(
            run_id, result.new_messages(), who=who, page=page, message=message, mode=mode, started_at=started_at,
            stop_reason="answered_after_price_retry" if deps.price_guard_trips else "answered",
            usage=result.usage, duration_s=time.perf_counter() - started,
            extra={
                "price_guard_trips": deps.price_guard_trips,
                "product_ids": output.product_ids[:MAX_PRODUCTS],
                "results_title": output.results_title,
                "reply": audit.short(output.reply),
            },
        )
    )
    return result


async def chat(message: str, history: list[ChatTurn], deps: ShopDeps) -> ChatResponse:
    """Run one chat turn and return the reply plus database-backed product cards."""
    result = await run_agent(message, history, deps, mode="json")
    return finish(result.output)


async def chat_stream(message: str, history: list[ChatTurn], deps: ShopDeps) -> AsyncIterator[dict]:
    """Run one chat turn, yielding events as they happen:

        {"type": "status", "text": "Checking stock…"}   a tool started
        {"type": "reset"}                              a new answer attempt started (e.g. after the price guard)
        {"type": "delta", "reply": "Yes, the Bas"}      the reply so far (full text, not just the new part)
        {"type": "done", "response": ChatResponse}      final reply + product cards

    Uses agent.run() with an event handler (not run_stream) so tool calls and
    price-guard retries behave exactly like the non-streaming route.
    """
    queue: asyncio.Queue = asyncio.Queue()
    attempts = 0

    async def on_events(ctx: RunContext[ShopDeps], events: AsyncIterable[AgentStreamEvent]) -> None:
        nonlocal attempts
        buffers: dict[int, str] = {}
        sent: dict[int, str] = {}
        last_status = ""
        async for event in events:
            if isinstance(event, FunctionToolCallEvent):
                text = TOOL_STATUS.get(event.part.tool_name)
                if text and text != last_status:  # parallel calls of one tool → one status line
                    last_status = text
                    await queue.put({"type": "status", "text": text})
            elif isinstance(event, PartStartEvent) and isinstance(event.part, ToolCallPart):
                if event.part.tool_name == OUTPUT_TOOL:
                    attempts += 1
                    buffers[event.index] = event.part.args_as_json_str() if event.part.args else ""
                    await queue.put({"type": "reset"})
                    if attempts > 1:
                        await queue.put({"type": "status", "text": "Double-checking that…"})
            elif isinstance(event, PartDeltaEvent) and event.index in buffers:
                delta = event.delta
                if isinstance(delta, ToolCallPartDelta) and isinstance(delta.args_delta, str):
                    buffers[event.index] += delta.args_delta
                    try:
                        reply = from_json(buffers[event.index], allow_partial="trailing-strings").get("reply", "")
                    except ValueError:
                        continue
                    if isinstance(reply, str) and reply != sent.get(event.index):
                        sent[event.index] = reply
                        await queue.put({"type": "delta", "reply": reply})

    async def run() -> None:
        try:
            result = await run_agent(message, history, deps, mode="stream", event_stream_handler=on_events)
            await queue.put({"type": "done", "response": finish(result.output)})
        except Exception as e:  # handed to the caller, which decides what the shopper sees
            await queue.put({"type": "error", "error": e})

    task = asyncio.create_task(run())
    try:
        while True:
            event = await queue.get()
            yield event
            if event["type"] in ("done", "error"):
                break
    finally:
        if not task.done():
            task.cancel()
