# AI Prompts Log — Homework 04: Campus Customs Shop + Chatbot

A running log of the prompts I gave the AI coding assistant for each problem.
Follow-up prompts are optional; when one is used, the "What was lacking" note explains in one sentence why it was needed.

---

## Problem 1: Vibe Coder Prompts

**Prompt:**

> I'm starting a project and want to give you the full context before we build anything. We'll work through it one step at a time, and I'll send each task separately. Don't write any code yet. For now, just confirm you understand the setup and suggest a project structure.
>
> **Project: Campus Customs Shop + Chatbot**
>
> I'm building a customer-facing online store for a merch shop called Campus Customs. It needs a built-in AI shopping assistant.
>
> **Tech stack:**
> - Frontend: React + Vite, written in TypeScript
> - Backend: Python with FastAPI
> - Chatbot: a PydanticAI agent running in the backend
> - AI calls: routed through Portkey using my `PORTKEY_API_KEY` from an environment variable. I'll use OpenAI models from the 5.6 or 6 series, possibly a stronger model for harder reasoning steps.
>
> **What shoppers should be able to do:**
> - Browse the product catalogue
> - Create an account and log in
> - Chat with the assistant about merch
> - See products the chatbot mentions show up on the page
> - Get accurate price and stock answers that come from the database. The agent must never make these up.
>
> **Data I have (in a `data/` folder):**
> - `data/campus_customs.db`: a SQLite database with three tables:
>   - `catalogue`: products, including the file path to each product image
>   - `inventory`: stock levels broken down by size
>   - `users`: accounts with hashed passwords (one test user already exists)
> - `data/products/`: product images whose paths match the `catalogue` table
>
> **Style and tone:** The site's look and the agent's knowledge should be modeled on yalebulldogblue.com (Yale-style colors, layout, and shop info).
>
> **Constraints:**
> - The project will be pushed to a public GitHub repo.
> - The database and product images must NOT be committed. Add them to `.gitignore` from the start.
> - Keep secrets like API keys in a `.env` file that is also gitignored.
>
> To start, please:
> 1. Confirm your understanding of the project.
> 2. Propose a clean folder structure for the frontend and backend.
> 3. Inspect the database schema (tables and columns) so we know what we're working with.

**Follow-up prompt (optional):**

> _[Paste the follow-up prompt, or delete this field if none]_

**What was lacking:** _[One sentence on why the follow-up was needed]_

---

## Problem 2: Analyze the Database

**Prompt:**

> Now let's work on Problem 2: Analyze the database.
>
> Look at data/campus_customs.db and help me understand the fields of each table, especially catalogue, inventory, and users.
>
> Start output/harness.md and write down each table and its fields, with one short line on why each field matters for the shop or the chatbot.
>
> I'll keep growing this harness file in later problems to cover models, tools, safety, and specs, so set it up in a way that's easy to add to.

**Follow-up prompt (optional):**

> _[Paste the follow-up prompt, or delete this field if none]_

**What was lacking:** _[One sentence on why the follow-up was needed]_

---

## Problem 3: Build the Campus Customs Website

**Prompt:**

> Now let's work on Problem 3: Build the Campus Customs website.
>
> Scaffold a React + Vite + TypeScript front end for Campus Customs. Add a nav bar at the top linking to: Home, Products, About Us, Log in, Create account.
>
> For the Home and About Us pages, pull Campus Customs-style wording from yalebulldogblue.com for inspiration, but write the actual page content in your own voice, don't copy the original site text.
>
> On the Products page, show product images from the catalogue, using the image paths in the database, along with basic info like name, price, and a short description.
>
> Make each product open a single-item page with a large image on one side and full product text on the other (description, price, sizes/stock if available). Clicking a card on the Products page should take the shopper to that single-item page.
>
> Add a chat interface in the bottom right of the site, a floating chat panel is fine. It doesn't need to talk to an agent yet, just a stub that will call the backend later.
>
> Start a simple FastAPI app in backend/main.py to serve products and images from the database. I'll grow it into the full agent backend in Problem 5, so keep it simple for now.

**Follow-up prompt (optional):**

> _[Paste the follow-up prompt, or delete this field if none]_

**What was lacking:** _[One sentence on why the follow-up was needed]_

---

## Problem 4: Create Account and Login

**Prompt:**

> Now let's work on Problem 4: Create account and login.
> Build a normal create-account / login flow.
> Create account should collect: first name, last name, email, password (and a confirm password field).
> Log in should take email and password.
> New accounts should go into the `users` table. Make sure passwords are stored securely, not in plain text, so they can't be accessed even if the database is compromised.
> There's already a test user seeded in the database I can use while building:
>
> - Email: `test@campuscustoms.yale.edu`
> - Password: `password`
>
> Help me confirm I can log in as that test user, and that a brand-new account I create also works end to end.
> Help me write harness explanation for me, add how auth works (what's stored for a user and how passwords are protected) to `output/harness.md`

**Follow-up prompt (optional):**

> _[Paste the follow-up prompt, or delete this field if none]_

**What was lacking:** _[One sentence on why the follow-up was needed]_

---

## Problem 5: PydanticAI Agent Backend

**Prompt:**

> Now let's work on Problem 5: PydanticAI agent backend.
> Build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into the front-end chat widget I already built. Put the API app in `backend/main.py`, that's the file I'll run with Uvicorn.
> Keep the agent as four files next to it, same idea as Homework 3:
>
> - `backend/prompts/prompt.md`: system prompt (I'll grow this file later)
> - `backend/agent.py`: agent entry / wiring
> - `backend/tools.py`: tools the agent can call
> - `backend/models.py`: Pydantic / PydanticAI structured types
>
> In `main.py`, expose a chat route so a message from the website returns a reply from the agent, plus whatever else is needed for products and auth. I have my AI model API key ready for the agent.
> Put Campus Customs voice and safety basics into `prompts/prompt.md`, I'll expand the tools and safety sections later. Start or update types in `models.py` for chat replies and product cards as needed.
> Make sure the backend runs from the `backend/` folder with:
>
> ```
> uvicorn main:app --reload --port 8000
> ```
>
> help me write the harness notes, add how the front end talks to FastAPI and how the agent is loaded (prompt file + model) to `output/harness.md`

---

## Problem 6: Tools: Product Info and Stock

**Prompt:**

> Now let's work on Problem 6: Tools: product info and stock.
> Give the agent tools that look up real information from `campus_customs.db`:
>
> - Product description
> - Price
> - How many are in stock (by size when the customer asks)
>
> The agent must use the database for this, it should not invent prices or quantities. If a size is out of stock, it should say so clearly.
> Expand `prompts/prompt.md` so the agent knows to call these tools for price and stock questions. Add or update return types in `models.py` as needed.
> help me write the harness explanation, list each tool and explain which model fields I chose for lookup results and why in `output/harness.md`

---

## Problem 7: Chat Search That Updates the Page

**Prompt:**

> Now let's work on Problem 7: Chat search that updates the page.
>
> When a customer asks about a type of item in the chat, for example "what hoodies do you have?", the agent should search the catalogue and the website should dynamically show the matching items as product cards (image, name, price, short info).
>
> This should work as an API contract: the agent returns structured product matches, and the front end renders them on the page.
>
> Make sure the single-item page behavior from Problem 3 still works for these dynamically loaded cards too, each product card, including the ones the chat just added to the page, should still open the detail view (large image + full info) when clicked.
>
> Update prompts/prompt.md so the agent knows to use this search-and-display behavior.
>
> help me write the harness explanation, update to explain how search results reach the page

---

## Problem 8: Customer Memory

**Prompt:**

> Now let's work on Problem 8: Customer memory.
>
> When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who it's chatting with (name, email), put that in agent deps or an equivalent clear pattern, and/or tools the agent can call.
>
> Also pass enough page context that if someone is on a product page and asks "do you have this in pink?", the agent knows which item they mean.
>
> Guests should still be able to chat, but history only needs to persist for logged-in users.
>
> help me write the harness explanation, document how user chat history is stored, what customer fields the agent sees, and how page context is passed in output/harness.md

---

## Problem 9: Usability Improvements

**Prompt:**

> Now let's work on Problem 9: Usability improvements.
> I want to choose and implement:
>
> - 2 front-end usability improvements (things that make the site look better or easier to use)
> - 2 agent/backend usability improvements (things that make the agent output better, more accurate, or safer, like new tools, or changes that make it faster or cheaper to run)
>
> First, suggest a few options for each category so I can pick which ones to build, rather than just picking for me.
> Once I choose, implement them and make sure they actually show up and work in the running app.
> Don't write the write-up for me, I'll document what I added and why it helps a Campus Customs shopper or the business in `output/usability.md` myself once I understand each improvement.

---

## Problem 10: Style the Website

**Prompt:**

> Now let's work on Problem 10: Style the website.
> I want to restyle my Campus Customs site with a "Varsity Locker Room" theme, think letterman jackets, chenille patches, hang tags, scoreboards. Like a real campus store on game day, not a generic-looking site. Keep all the existing functionality, content, and file structure working, just update the styling and add some small UI touches.
> Some ideas for the vibe:
>
> - Bold, collegiate-style headings and a clean body font, navy and gold as the main colors with cream backgrounds, red only for sale/low-stock badges
> - A scrolling promo banner at the top like "Free shipping over $50 · Homecoming drop live"
> - A hero section with a bold headline and one standout CTA button
> - Product cards that look like hang tags, little details like a punched hole, a slight tilt that straightens on hover, maybe a "Fan Favorite" or "New Drop" badge here and there
> - Nice subtle motion: cards fading in as you scroll, a little celebration (like confetti) when something's added to cart, but respecting reduced-motion settings
> - The chatbot should feel like a friendly campus store clerk, maybe even give it a name and a mascot-ish avatar, with chat bubbles that feel like texting and some quick-reply buttons for common questions
>
> Keep it fully responsive, keep text readable and accessible, and don't break any existing IDs, classes, or JS hooks the app relies on.
> When you're done, list every file you changed and briefly explain what you did.
> I'll write up what changed and why it should help customers stick around and buy in `output/design.md` myself once I see the result.

---

## Problem 11: Site Testing (App Check)

**Prompt:**

> Now let's work on Problem 11: Site testing (app check).
> I need to test the live site and document it in `output/app_check.html`, a page I can double-click to open. It should include clear screenshots and short captions for:
>
> 1. Chat checking the inventory level of an item (showing honest stock/price pulled from the DB)
> 2. The dynamic search-result cards appearing after a category question (like "what hoodies do you have?")
> 3. One of the usability features I added in Problem 9
>
> Make the HTML easy to grade: a heading for each check, the screenshot, and one or two sentences on what the screenshot proves.
> Put the screenshot image files in `output/app_check_images/` and link them from `app_check.html` with relative paths, for example `app_check_images/inventory.png`.
> Help me take the screenshots from the running app for each of these three checks, then build the HTML page with them.

---

## Problem 12: Audit Trail, Safety, Finish Harness

**Prompt:**

> Now let's work on Problem 12: Audit trail, safety, finish harness.
> Keep an append-only `output/audit_trail.json` log of agent-loop activity (time, tool name, short args/result, stop reason). It should not get wiped between runs.
> Also add safety rules to `prompts/prompt.md`. Here are some I want included, feel free to suggest more:
>
> - Never make up prices, stock levels, or product details, always use tool/database lookups
> - Don't share or ask for sensitive customer info (passwords, payment details, etc.) in chat
> - Decline requests unrelated to Campus Customs products or shopping, stay on topic
> - Be honest about what's out of stock rather than suggesting unavailable items
> - If unsure about something, say so rather than guessing
>
> Finish `output/harness.md` so it's clear how the whole system works. Include:
>
> - The model fields in `models.py` and why they were chosen
> - The tools and abilities the agent has
> - The safety rules we added
> - Specs like loop limits, result caps, which models are used, and how to run the front end and backend together

---

## Problem 13: Push to GitHub and Submit the URL

**Prompt:**

> Now let's finish up with Problem 13: Push to GitHub and submit the URL.
> Help me put my code in a folder named `hw4` and push it to a public GitHub repository, so I can submit the repo URL on Canvas instead of a zip.
> Make sure my real `.env`, `campus_customs.db`, and product images are not included in the repo. Set up `.gitignore` for that, and include `.env.example` with placeholders only.
> The expected layout is: `hw4/` with `AI_prompts.md`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `frontend/`, `backend/` (`main.py`, `agent.py`, `models.py`, `tools.py`, `prompts/prompt.md`), and `output/` (`harness.md`, `design.md`, `usability.md`, `app_check.html`, `app_check_images/`, `audit_trail.json`). The local-only data pack (not committed) is `data/campus_customs.db` and `data/products/`.
> The agent itself is four files under `backend/`: `prompts/prompt.md`, `agent.py`, `tools.py`, and `models.py`.
> Write `README.md` so it explains how to run the front end and back end after placing the data pack locally.
> Walk me through initializing the repo, committing, creating the GitHub repo, and pushing, since I'll need to do the actual GitHub steps myself.
