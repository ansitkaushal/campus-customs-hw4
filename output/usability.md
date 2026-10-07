# Usability Improvements: Campus Customs

I made eight improvements, four on the front end and four on the agent and backend. I tested each one in the running app.

| # | Improvement | Area | Main files |
|---|---|---|---|
| 1 | Suggested-question chips | Front end | `ChatWidget.tsx` |
| 2 | "Ask about this item" on the product page | Front end | `ProductPage.tsx`, `ChatUIContext.tsx` |
| 3 | Stock shown on product cards | Front end | `ProductCard.tsx`, `/api/products` |
| 4 | Sort and price filter | Front end | `Products.tsx` |
| 5 | Price fact-check guard | Agent / backend | `agent.py` |
| 6 | Similar-items tool | Agent / backend | `tools.py` |
| 7 | Streaming replies | Agent / backend | `main.py`, `agent.py` |
| 8 | Cheaper turns and a rate limit | Agent / backend | `main.py`, `agent.py` |

---

## Front end

### 1. Suggested-question chips

**What I added:** Four starter questions show in the chat widget before the shopper sends their first message. Product pages get their own chips, such as "Is this in stock in M?". Clicking a chip sends that question, and the chips go away after the first message. (`ChatWidget.tsx`)

**Why it helps:** A blank chat box doesn't tell shoppers what the assistant can do. The chips show them the questions it handles well, like sizes, stock and gift ideas, so they can start with one click and don't have to work out what to type. More shoppers using the chat means more of them get to the right product.

### 2. "Ask about this item" on the product page

**What I added:** A box under the size table with two buttons. "Ask about this item" opens the chat with "Do you have this in size " already typed and the cursor in place. "Find similar" asks the assistant for related products. (`ProductPage.tsx`, `ChatUIContext.tsx`)

**Why it helps:** Shoppers usually have their question while they're looking at a particular hoodie. Opening chat with that product already in the question saves them from naming it, and the agent gets a clear question to answer. "Find similar" keeps a shopper browsing when the item isn't quite what they wanted, so they don't leave the page.

### 3. Stock shown on product cards

**What I added:** Each product card has a row of size chips. Sold-out sizes are crossed out and sizes with 1–3 left are amber. Products with 3 or fewer sizes left get a corner badge (21 of 102 products). Product cards in the chat use the same size row. (`ProductCard.tsx`, `/api/products`)

**Why it helps:** Shoppers can see whether their size is available from the grid, without clicking into every product or finding out at checkout. The amber chips and the badge tell them some sizes are running out, which encourages them to buy sooner. I first badged any product low in any size, but that put a badge on 42 of 102 products, which was too many to mean anything. I limited it so the badge points to products that really are close to selling out.

### 4. Sort and price filter

**What I added:** The Products page can be sorted by price, name or most sizes in stock. It also has a max-price slider. These settings are saved in the URL. (`Products.tsx`)

**Why it helps:** Students are often shopping on a budget. With the slider, a shopper sees only what they can afford: at $60 there are 58 items, sorted low to high. Sorting by most sizes in stock puts items they're likely to find in their size first. Because the settings are in the URL, a shopper can share a filtered view with a friend or come back to it later.

---

## Agent and backend

### 5. Price fact-check guard

**What I added:** `check_prices` in `agent.py` checks every dollar amount in the agent's answer against the catalogue before the shopper sees it. If a price is wrong, the answer is rejected and the agent tries again. Budgets the shopper typed themselves (for example "under $60") are let through. In a test, I put a wrong price ($40.00) into an earlier message. The agent repeated it, the guard rejected that answer, and on retry the agent looked up the price and gave the correct $68.00.

**Why it helps:** A wrong price hurts the shopper's trust and can cause disputes at checkout. The guard makes sure every price the assistant states matches the store's catalogue.

### 6. Similar-items tool

**What I added:** `find_similar_products` in `tools.py` returns in-stock alternatives in the same category, matched to the shopper's size and color when they give them. Matches are scored so that uncommon shared words like "hockey" count for more than common ones like "hoodie" or "college". When the Ice Hockey hoodie was sold out in M, the agent showed two hoodies that were in stock in M.

**Why it helps:** "Sold out" usually ends the visit. Offering a close match the shopper can buy right away turns that into a sale and saves them from searching on their own.

### 7. Streaming replies

**What I added:** A new `POST /api/chat/stream` endpoint and `chat_stream()` in `agent.py`. The chat shows live status lines such as "Searching the catalogue…" while the agent works, then the reply text as it's written. If the price guard rejects an answer, that text is cleared and the corrected answer replaces it.

**Why it helps:** Most of the wait comes from the catalogue lookups before the model starts writing. The text itself streams in about 0.4 seconds. Without the status line, shoppers see nothing happening and may think the chat is broken. With it, they can see the assistant is working, so the same wait feels shorter.

### 8. Cheaper turns and a rate limit

**What I added:** The agent now gets the last 12 messages instead of 20, and long earlier replies are shortened. Each chat logs its time, tokens, cached tokens, cost and any guard rejections. Each shopper or guest can send up to 10 messages a minute. The 11th message gets a friendly "please wait 55 seconds" reply. (`main.py`, `agent.py`)

**Why it helps:** For the business, a typical guest question now costs about $0.0008, since roughly 95% of the input tokens come from the cache. The log line shows the cost of every chat, so a surprise cost like one 45k-token run gets noticed. The rate limit stops a script or a bad actor from running up the bill. For shoppers, a shorter history means faster replies, and the wait message tells them what to do instead of just showing an error.

---

## Known limitations

- The agent doesn't always follow the prompt. Once, it said the hockey hoodie was sold out but didn't call the similar-items tool. Another time, the "Gift ideas under $60" chip got a list in chat instead of product results. The tools work whenever the agent uses them, but the prompt rules could be tighter.
- The rate limit is stored in memory, so it resets when the server restarts.
- Test data: testing added extra messages to Test User's saved chat history.
