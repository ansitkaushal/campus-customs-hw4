# Campus Customs: Shop + AI Shopping Assistant (MGT 409, Homework 4)

An online store for **Campus Customs**, a New Haven shop selling officially licensed Yale apparel, with a built-in AI shopping assistant called **Benny**.

- **Frontend:** React + Vite + TypeScript (`frontend/`), styled as "The Varsity Locker Room"
- **Backend:** Python + FastAPI (`backend/main.py`)
- **Agent:** a PydanticAI agent that calls OpenAI models through Portkey, made of four files in `backend/`:
  - `prompts/prompt.md`: system prompt (voice, tools, safety rules)
  - `agent.py`: agent wiring (model, prompt, price fact-check, loop limits, streaming)
  - `tools.py`: tools the agent calls (search, product info, stock, similar items, customer profile)
  - `models.py`: Pydantic / PydanticAI structured types
- **Data:** a local SQLite database plus product images (the "data pack"), **not** included in this repo

Shoppers can browse the catalogue, create an account and log in, and chat with Benny. Benny answers price and stock questions from the database (never guessed), shows the products it finds as cards on the page, remembers logged-in customers, and understands "this one" on a product page.

The full design is in **[`output/harness.md`](output/harness.md)**.

---

## Repository layout

```
hw4/
├── AI_prompts.md          # prompts used for each problem
├── requirements.txt       # backend Python packages
├── .env.example           # environment variable names (placeholders only)
├── .gitignore
├── README.md
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app, run with: uvicorn main:app --reload
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   ├── prompts/
│   │   └── prompt.md
│   ├── auth.py            # create account / log in (PBKDF2 password hashing)
│   ├── audit.py           # append-only audit trail of agent activity
│   └── db.py              # SQLite paths + connection helper
└── output/
    ├── harness.md         # how the whole system works
    ├── design.md          # the visual redesign
    ├── usability.md       # usability improvements
    ├── app_check.html     # app test report (double-click to open)
    ├── app_check_images/  # screenshots linked from app_check.html
    └── audit_trail.json   # append-only log of agent runs
```

---

## Requirements

- **Python 3.11+** (developed on 3.14)
- **Node.js 20+** and npm (developed on Node 24)
- A **Portkey API key** with access to OpenAI models (default model: `gpt-5.6-luna`)
- The **data pack** (from Canvas; not in this repo)

---

## Setup

### 1. Place the data pack

Put the data pack in a `data/` folder at the top level of this repo, so the paths look exactly like this:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # images referenced by the catalogue (e.g. basic-hoodie-big-yale.jpg)
```

`data/` is gitignored, so it will never be committed. The backend reads the database from `hw4/data/campus_customs.db` and serves images from `hw4/data/products/`.

### 2. Create your `.env`

```bash
cp .env.example .env
```

Then edit `.env` and fill in:

| Variable | Required | What it's for |
|---|---|---|
| `PORTKEY_API_KEY` | Yes | Model calls for the chatbot |
| `AUTH_SECRET` | Recommended | Signs login cookies. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`. If missing, a random one is used and everyone is logged out on restart. |
| `CHAT_MODEL` | No | Use a different model (default `gpt-5.6-luna`) |

`.env` is gitignored. Never commit it.

### 3. Install the backend

From the `hw4/` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Install the frontend

```bash
cd frontend
npm install
cd ..
```

---

## Run (two terminals)

The frontend and backend run side by side. Vite forwards `/api` and `/images` requests to FastAPI, so **both must be running**.

**Terminal 1: backend (port 8000)**

```bash
cd hw4
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

Check it's up: <http://localhost:8000/api/health> → `{"status":"ok"}`

**Terminal 2: frontend (port 5173)**

```bash
cd hw4/frontend
npm run dev
```

Open **<http://localhost:5173>**.

### Try it

- **Test login:** `test@campuscustoms.yale.edu` / `password` (seeded in the database), or create a new account.
- **Ask Benny** (bottom-right): "What hoodies do you have?", "Is this in stock in M?" on a product page, "Gift ideas under $60".
- **Browse** Products, sort by price, filter by max price, open any card for sizes and stock.

---

## Notes

- **Secrets and data stay local:** `.env`, `data/`, `*.db`, `.venv/`, and `node_modules/` are all gitignored.
- **Audit trail:** every agent run is appended to `output/audit_trail.json` (emails and long numbers redacted). It's never wiped.
- **Rate limit:** 10 chat messages per minute per shopper or guest.
- **Production build of the frontend:** `cd frontend && npm run build` (output in `frontend/dist/`, gitignored).
