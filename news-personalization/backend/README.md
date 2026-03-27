# 🗞️ My ET — Personalized Newsroom Backend

> *"Same news. Different experience for every user."*

Built for the **Economic Times Agentic AI Hackathon 2026**.

---

## 🧠 What This Project Does

Business news in 2026 is still delivered like it's 2005 — same article for everyone.
This backend powers an AI system that reads your profile and delivers a **fundamentally
different news experience**:

| User Type | What They Get |
|-----------|---------------|
| 🧑‍🎓 Student (Beginner) | Simple explanations + "Why you should care" |
| 🧑‍🎓 Student (Intermediate) | Deeper context with terminology explained |
| 📈 Investor | Market impact + stocks to watch + action points |
| 🚀 Founder | Funding signals + competitor moves + startup angles |

The system **learns from every click** — the more you use it, the smarter it gets.

---

## ⚙️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API Server | **FastAPI** | Fast, async, auto-docs at `/docs` |
| Background Jobs | **Celery** | Fetches news every 15 min without blocking API |
| Cache + Broker | **Redis** | Instant feed retrieval, user profile storage |
| Database | **PostgreSQL** | Persistent user data and article storage |
| AI / LLM | **Gemini 1.5 Flash (FREE)** | Rewrites articles per user profile |
| News Source | **ET RSS Feeds (FREE)** | Real Economic Times articles, no API key needed |
| Containers | **Docker + Docker Compose** | One command to run everything |

---

## 🏗️ Project Structure

```
my-et-backend/
│
├── app/
│   ├── main.py                  ← FastAPI app entry point
│   ├── config.py                ← All settings (reads from .env)
│   ├── database.py              ← PostgreSQL connection
│   │
│   ├── models/
│   │   └── user.py              ← User + Article DB models
│   │
│   ├── routes/
│   │   ├── auth.py              ← /signup, /login, /profile
│   │   └── news.py              ← /news/feed/{user_id}  ← MAIN ENDPOINT
│   │
│   ├── agents/
│   │   └── orchestrator.py      ← 🤖 THE AGENTIC BRAIN
│   │
│   ├── services/
│   │   ├── redis_service.py     ← Cache helpers
│   │   ├── news_service.py      ← Fetch + rank news (ET RSS)
│   │   └── ai_service.py        ← Gemini rewrites
│   │
│   └── celery_app/
│       └── celery_config.py     ← Background tasks
│
├── docker-compose.yml           ← Spins up ALL services
├── Dockerfile                   ← Container definition
├── requirements.txt             ← Python dependencies
├── .env.example                 ← Copy this to .env
└── .gitignore
```

---

## 🚀 Setup Guide (Step by Step)

### Step 1 — Get Your FREE Gemini API Key

1. Go to → **https://aistudio.google.com/app/apikey**
2. Click **"Create API Key"**
3. Copy the key (starts with `AIza...`)

> 💡 No credit card needed. Gemini 1.5 Flash has a generous free tier.

---

### Step 2 — Clone and Configure

```bash
# Clone the project
git clone <your-repo-url>
cd my-et-backend

# Create your .env file from the template
cp .env.example .env
```

Now open `.env` and paste your Gemini key:

```env
GEMINI_API_KEY=AIzaSy...your_key_here
```

---

### Step 3 — Start Everything with Docker

```bash
docker-compose up --build
```

This single command starts:
- ✅ FastAPI server on `http://localhost:8000`
- ✅ Celery worker (background jobs)
- ✅ Celery Beat (scheduler)
- ✅ Redis
- ✅ PostgreSQL

Wait ~30 seconds for everything to initialize.

---

### Step 4 — Verify It's Working

Open your browser:

```
http://localhost:8000/docs
```

You'll see the **Swagger UI** — an interactive API explorer where you can test all endpoints.

Also check health:
```
http://localhost:8000/health
```

---

## 📡 API Endpoints

### Auth

| Method | URL | What it does |
|--------|-----|-------------|
| `POST` | `/auth/signup` | Register + set role/interests |
| `POST` | `/auth/login` | Login, get JWT token |
| `GET`  | `/auth/profile/{user_id}` | View profile |
| `PUT`  | `/auth/profile/{user_id}` | Update interests/role |

### News Feed (the main feature)

| Method | URL | What it does |
|--------|-----|-------------|
| `GET` | `/news/feed/{user_id}` | Get personalized feed 🌟 |
| `POST` | `/news/engage/{user_id}` | Record click/read/skip |
| `DELETE` | `/news/feed/{user_id}/cache` | Force refresh feed |
| `GET` | `/news/pool/status` | Check Celery news pool |

---

## 🧪 Quick Test (copy-paste these)

### 1. Sign up as a student

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "test123",
    "role": "student",
    "interests": ["AI", "startups"],
    "level": "beginner"
  }'
```

### 2. Sign up as an investor

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "investor@test.com",
    "password": "test123",
    "role": "investor",
    "interests": ["markets", "finance"],
    "level": "intermediate"
  }'
```

### 3. Get the student's personalized feed

```bash
curl http://localhost:8000/news/feed/1
```

### 4. Get the investor's personalized feed

```bash
curl http://localhost:8000/news/feed/2
```

**Both users get the same news source — but completely different explanations.**

---

## 🤖 How the Agentic AI Works

```
User requests feed
       ↓
 [Orchestrator]  ← reads profile from Redis
       ↓
 [Check Cache]   ← return instantly if fresh (< 15 min)
       ↓
 [News Pool]     ← loaded from Redis (filled by Celery every 15 min)
       ↓
 [Personalizer Agent]
    • score each article vs user interests
    • weight by past engagement (learned behaviour)
    • pick top 10
       ↓
 [Rewriter Agent]  ← calls Gemini 1.5 Flash (FREE)
    • student → simple explanation + why it matters
    • investor → market signals + action points
    • founder → startup angle + opportunity/threat
       ↓
 [Cache in Redis]  ← next request is instant
       ↓
 Return personalized feed
```

The system is **agentic** because:
1. It **plans** — orchestrator decides which agents to run
2. It **uses tools** — agents use RSS, Redis, Gemini
3. It **learns** — engagement signals update the profile
4. It **acts autonomously** — Celery refreshes news without any user trigger

---

## 📊 What Makes This "WOW" for Judges

- ✅ **Not just recommendations** — actual content rewriting per user
- ✅ **Real news** — live ET RSS feeds, not dummy data
- ✅ **Learns over time** — click = preference update = smarter next feed
- ✅ **Production-grade** — Docker, Redis caching, async API, background workers
- ✅ **Free LLM** — no paid API needed, works for anyone

---

## 🛠️ Common Issues

**Port already in use?**
```bash
docker-compose down && docker-compose up --build
```

**Celery not fetching news?**
```bash
# Check Celery logs
docker logs my_et_celery
```

**Database issues?**
```bash
# Reset everything
docker-compose down -v
docker-compose up --build
```

---

## 👨‍💻 Author

Built for Economic Times Agentic AI Hackathon 2026.
