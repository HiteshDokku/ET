"""Personalized News Intelligence Agent.

Transforms static user profile data into a high-relevance news feed by:
1. Ingesting user Role, Interests, Experience Level
2. Generating targeted Google News RSS queries (LLM-expanded)
3. Fetching articles via feedparser (lightweight, no Selenium)
4. Evaluating relevance against specific user interests (LLM)
5. Filtering by complexity / experience level (LLM)
6. Performing gap analysis across interest areas (LLM)
7. Generating a synthesis briefing with follow-ups (LLM)
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional
from dateutil import parser as dateparser

import feedparser

from app.intel.llm_client import ask_llm, ask_llm_fast

# ── Google News RSS base ─────────────────────────────────────────
GOOGLE_RSS_BASE = "https://news.google.com/rss/search?hl=en-IN&gl=IN&ceid=IN:en&q="

# ── Role-specific query suffixes ─────────────────────────────────
ROLE_QUERY_HINTS = {
    "investor":  ["equity", "market analysis", "portfolio", "valuation", "returns"],
    "founder":   ["startup opportunity", "funding round", "venture", "disruption"],
    "student":   ["explained", "trends", "overview", "analysis", "introduction"],
}

# ── System prompts ───────────────────────────────────────────────

QUERY_GEN_PROMPT = """You are a personalized news intelligence agent.
Given a user profile (role, interests, experience level), generate targeted
search queries for Google News RSS.

RULES:
- Each query must be 1-3 keyword terms. NO full sentences or questions.
- Expand core interests into related semantic terms.
  Examples: "Startups" → "Series A funding", "Unicorn valuation"
           "AI" → "LLM breakthrough", "generative AI India"
           "Crypto" → "bitcoin regulation India", "DeFi protocol"
- Tailor queries to the user's Role:
  - Investor → append financial/market terms
  - Founder → append opportunity/disruption terms  
  - Student → append trend/overview terms
- Generate 3-4 queries PER interest area to ensure broad coverage.
- Return ONLY valid JSON: {"queries": ["query1", "query2", ...]}
"""

EVALUATE_PROMPT = """You are a personalized news intelligence agent evaluating article relevance.

Given a user profile and a list of articles, evaluate each article:
1. RELEVANCE: Does the article title/summary DIRECTLY impact the user's specific interests?
2. COMPLEXITY: Filter based on experience level:
   - "beginner" → reject hyper-technical whitepapers, jargon-heavy analysis
   - "intermediate" → accept most content
   - "advanced" → reject basic definitions, introductory explainers
3. FRESHNESS: Prefer recent articles.

Return ONLY valid JSON:
{
  "kept_articles": ["temp_id_1", "temp_id_2"],
  "rejections": [
    {"temp_id": "temp_id_3", "reason": "Too basic for advanced user"},
    {"temp_id": "temp_id_4", "reason": "Not relevant to user interests"}
  ]
}
"""

GAP_ANALYSIS_PROMPT = """You are a personalized news intelligence agent performing gap analysis.

Given a user's interests and the articles already collected, determine:
1. Are any interest areas completely missing or underrepresented?
2. Is there sufficient diversity of perspectives?

Return ONLY valid JSON:
{
  "gaps_found": true/false,
  "underrepresented_interests": ["interest1"],
  "next_angle": "suggested query angle to fill the gap",
  "reasoning": "brief explanation"
}
"""

BRIEFING_PROMPT = """You are a personalized financial analyst for an intelligence platform.

Create a deep, personalized intelligence briefing from the provided articles,
tailored specifically to the user's profile.

User Profile:
- Role: {role}
- Interests: {interests}
- Experience Level: {level}

INSTRUCTIONS:
- Synthesize across ALL articles into a unified narrative.
- Frame insights specifically for the user's role:
  - Investor → market implications, portfolio actions, risk assessment
  - Founder → opportunities, threats, competitive landscape
  - Student → key concepts, trends to watch, learning pointers
- Match complexity to user's level:
  - Beginner → simple language, avoid jargon, explain key terms
  - Intermediate → balanced depth, some technical detail
  - Advanced → deep analysis, quantitative points, contrarian views
- Be specific and actionable, never generic.

Return ONLY valid JSON:
{{
  "briefing": {{
    "Executive Summary": "...",
    "Key Insights": ["insight 1", "insight 2", "insight 3"],
    "Impact on Your Interests": "... (specifically tied to {interests})",
    "Action Items": "... (role-appropriate actions for a {role})",
    "What To Watch": "... (forward-looking, interest-specific)"
  }},
  "followups": ["Question 1?", "Question 2?", "Question 3?"]
}}
"""


def _parse_date(entry) -> Optional[datetime]:
    """Safely parse publish date from RSS entry."""
    try:
        if hasattr(entry, "published"):
            return dateparser.parse(entry.published)
    except Exception:
        pass
    return datetime.utcnow()


def _fetch_rss_articles(query: str, max_articles: int = 8) -> list[dict]:
    """Fetch articles from Google News RSS for a keyword query."""
    url = GOOGLE_RSS_BASE + query.replace(" ", "+")
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries[:max_articles]:
        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "")
        link = getattr(entry, "link", "")

        # Google News RSS includes source in the entry
        source_obj = getattr(entry, "source", None)
        if source_obj and hasattr(source_obj, "get"):
            source = source_obj.get("title", "Google News")
        elif hasattr(source_obj, "title"):
            source = source_obj.title
        else:
            source = "Google News"

        if title and link:
            articles.append({
                "temp_id": str(uuid.uuid4()),
                "title": title,
                "summary": summary[:500] if summary else "",
                "url": link,
                "source": source,
                "published": str(_parse_date(entry)),
                "query_used": query,
            })

    return articles


class PersonalizedIntelAgent:
    """Agentic loop: Profile → Queries → Scrape → Evaluate → Gap → Briefing."""

    def __init__(self, profile: dict):
        self.role = profile.get("role", "student")
        self.interests = profile.get("interests", [])
        self.level = profile.get("level", "beginner")
        self.profile = profile

        self.all_articles: list[dict] = []
        self.kept_articles: list[dict] = []
        self.seen_urls: set[str] = set()
        self.all_queries: list[str] = []
        self.rejections: list[dict] = []
        self.max_iterations = 3

    async def run(self) -> dict:
        """Execute the full personalized intelligence pipeline."""
        print(f"\n🧠 PersonalizedIntelAgent started")
        print(f"   Role: {self.role} | Interests: {self.interests} | Level: {self.level}")

        if not self.interests:
            return self._empty_response("No interests specified. Please set up your profile first.")

        for iteration in range(self.max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}/{self.max_iterations}")

            # ── Step 1: Generate queries ─────────────────────────
            queries = await self._generate_queries(iteration)
            self.all_queries.extend(queries)

            # ── Step 2: Fetch articles from Google News RSS ──────
            new_articles = []
            for query in queries:
                print(f"   🔍 Fetching RSS: '{query}'")
                fetched = _fetch_rss_articles(query, max_articles=10)
                for art in fetched:
                    if art["url"] not in self.seen_urls:
                        self.seen_urls.add(art["url"])
                        new_articles.append(art)
                await asyncio.sleep(0.3)  # gentle rate limit

            self.all_articles.extend(new_articles)
            print(f"   📦 Fetched {len(new_articles)} new unique articles")

            if not new_articles:
                print("   ⚠️  No new articles found this iteration")
                continue

            # ── Step 3: Evaluate relevance + complexity ──────────
            kept_ids = await self._evaluate_articles(new_articles)
            for art in new_articles:
                if art["temp_id"] in kept_ids:
                    self.kept_articles.append(art)

            print(f"   ✅ Kept {len(kept_ids)}/{len(new_articles)} articles")

            # ── Step 4: Gap analysis ─────────────────────────────
            if iteration < self.max_iterations - 1:
                has_gaps = await self._analyze_gaps()
                if not has_gaps:
                    print("   ✅ Sufficient coverage. Stopping early.")
                    break
                else:
                    print("   🔄 Gaps detected — running another iteration")
                    await asyncio.sleep(0.5)

        # ── Step 5: Generate personalized briefing ───────────────
        if not self.kept_articles:
            return self._empty_response("No relevant articles found for your interests. Try broadening your profile.")

        briefing_result = await self._generate_briefing()

        print(f"\n🎯 Agent finished. {len(self.kept_articles)} articles curated from {len(self.all_articles)} fetched.\n")

        return {
            "profile_used": {
                "role": self.role,
                "interests": self.interests,
                "level": self.level,
            },
            "queries_generated": self.all_queries,
            "articles_evaluated": len(self.all_articles),
            "articles_kept": len(self.kept_articles),
            "gaps_found": len(self.all_queries) > len(self.interests) * 3,
            "briefing": briefing_result.get("briefing", {}),
            "followups": briefing_result.get("followups", []),
            "articles": [
                {
                    "title": a["title"],
                    "url": a["url"],
                    "source": a["source"],
                    "published": a.get("published", ""),
                    "query_used": a.get("query_used", ""),
                    "summary": a.get("summary", "")[:200],
                }
                for a in self.kept_articles
            ],
        }

    # ─── Internal agent actions ─────────────────────────────────

    async def _generate_queries(self, iteration: int) -> list[str]:
        """LLM generates targeted queries from user profile."""
        role_hints = ROLE_QUERY_HINTS.get(self.role, ROLE_QUERY_HINTS["student"])

        prompt = f"""User Profile:
- Role: {self.role}
- Interests: {', '.join(self.interests)}
- Experience Level: {self.level}
- Role-specific terms to consider: {', '.join(role_hints)}

Iteration: {iteration + 1}
Articles already collected: {len(self.kept_articles)}
"""
        if iteration == 0:
            prompt += "\nThis is the FIRST iteration. Generate 3-4 queries PER interest to get broad initial coverage."
        else:
            covered = [a.get("query_used", "") for a in self.kept_articles]
            prompt += f"\nQueries already used: {covered}"
            prompt += "\nGenerate queries for MISSING angles or underrepresented interests."

        try:
            res = await ask_llm_fast(QUERY_GEN_PROMPT, prompt)
            queries = res.get("queries", [])
            # Validate: only short keyword queries
            validated = [q for q in queries if isinstance(q, str) and len(q.split()) <= 5]
            return validated if validated else [interest + " India" for interest in self.interests[:3]]
        except Exception as e:
            print(f"   ⚠️ Query generation failed: {e}")
            return [interest + " India news" for interest in self.interests[:3]]

    async def _evaluate_articles(self, articles: list[dict]) -> list[str]:
        """LLM evaluates each article for relevance + complexity fit."""
        article_list = "\n".join([
            f"ID: {a['temp_id']} | Title: {a['title']} | Source: {a['source']} | Summary: {a.get('summary', '')[:150]}"
            for a in articles
        ])

        prompt = f"""User Profile:
- Role: {self.role}
- Interests: {', '.join(self.interests)}
- Experience Level: {self.level}

Articles to evaluate:
{article_list}

Evaluate each article for relevance to the user's interests AND appropriate complexity for their level.
Return kept_articles (list of IDs) and rejections (list of {{temp_id, reason}})."""

        try:
            res = await ask_llm_fast(EVALUATE_PROMPT, prompt)
            kept = res.get("kept_articles", [])
            self.rejections.extend(res.get("rejections", []))
            return kept
        except Exception as e:
            print(f"   ⚠️ Evaluation failed: {e}")
            # Fallback: keep all
            return [a["temp_id"] for a in articles]

    async def _analyze_gaps(self) -> bool:
        """LLM checks if all interest areas are covered."""
        if len(self.kept_articles) < 2:
            return True  # definitely need more

        titles = [a["title"] for a in self.kept_articles]
        queries_used = list(set(a.get("query_used", "") for a in self.kept_articles))

        prompt = f"""User Interests: {', '.join(self.interests)}
Articles collected so far ({len(self.kept_articles)}):
{chr(10).join(f'- {t}' for t in titles)}

Queries already used: {queries_used}

Are any interest areas completely missing or underrepresented?
If gaps exist, suggest the next query angle to fill them."""

        try:
            res = await ask_llm_fast(GAP_ANALYSIS_PROMPT, prompt)
            return res.get("gaps_found", False)
        except Exception as e:
            print(f"   ⚠️ Gap analysis failed: {e}")
            return len(self.kept_articles) < 4

    async def _generate_briefing(self) -> dict:
        """LLM generates a personalized synthesis briefing."""
        articles_text = ""
        for i, article in enumerate(self.kept_articles[:8]):  # cap at 8
            articles_text += f"""
Article {i + 1}
Title: {article.get('title', '')}
Source: {article.get('source', '')}
Summary: {article.get('summary', '')}
"""

        interests_str = ", ".join(self.interests)
        system_prompt = BRIEFING_PROMPT.format(
            role=self.role,
            interests=interests_str,
            level=self.level,
        )

        user_prompt = f"Below are {len(self.kept_articles[:8])} curated articles matching this user's interests.\n\n{articles_text}"

        try:
            parsed = await ask_llm(system_prompt, user_prompt)
            return {
                "briefing": parsed.get("briefing", {}),
                "followups": parsed.get("followups", []),
            }
        except Exception as e:
            print(f"   ⚠️ Briefing generation failed: {e}")
            return {
                "briefing": {"Executive Summary": "Failed to generate briefing. Please try again."},
                "followups": [],
            }

    def _empty_response(self, message: str) -> dict:
        """Return a structured empty response."""
        return {
            "profile_used": {
                "role": self.role,
                "interests": self.interests,
                "level": self.level,
            },
            "queries_generated": [],
            "articles_evaluated": 0,
            "articles_kept": 0,
            "gaps_found": False,
            "briefing": {
                "Executive Summary": message,
                "Key Insights": [],
                "Impact on Your Interests": "N/A",
                "Action Items": "N/A",
                "What To Watch": "N/A",
            },
            "followups": [],
            "articles": [],
        }
