"""Autonomous Scraping Agent — Multi-Interest Dashboard Mode + LLM Ranking.

Pipeline:
1. Iterate through ALL user interests generating targeted RSS queries
2. Fetch Google News RSS (lightweight, no Selenium)
3. LLM evaluates relevance per batch
4. Gap analysis checks interest coverage → re-iterates if needed
5. **LLM Final Ranking**: ranks ALL collected articles by relevance,
   assigns matched_interest via AI reasoning (not keyword math),
   and saves the curated result for Redis caching
"""

import asyncio
import uuid
import feedparser
import logging
from datetime import datetime
from typing import Optional
from dateutil import parser as dateparser

from app.intel.llm_client import ask_llm_fast
from app.models.intel import ArticleInput

logger = logging.getLogger(__name__)

# Google News RSS base URL
GOOGLE_RSS_BASE = "https://news.google.com/rss/search?hl=en-IN&gl=IN&ceid=IN:en&q="

AGENT_SYSTEM_PROMPT = """You are an autonomous AI Scraping Agent for a personalized news dashboard.
You will receive user interests and the current state of gathered articles. 

You must return a JSON response depending on the action required:

IF Action == 'Generate Queries':
{
  "action": "search",
  "queries": ["keyword1 keyword2", "keyword3"]
}
IMPORTANT: Queries MUST be short keyword-only terms (1-3 words max). 
Do NOT use full sentences, questions, or long phrases.
Good: "RBI rate cut", "Adani Hindenburg", "AI startups India"
Bad: "What is the impact of RBI rate cuts on the Indian economy?"
Generate 2-3 queries PER interest area to ensure broad coverage.

IF Action == 'Evaluate Articles':
{
  "action": "evaluate",
  "kept_articles": ["id1", "id2"]
}

IF Action == 'Analyze Gaps':
{
  "action": "analyze",
  "gaps_found": true/false,
  "underrepresented": ["interest1"],
  "reasoning": "Explain which interests lack coverage."
}
"""

RANKER_SYSTEM_PROMPT = """You are an Expert News Curator for a personalized dashboard.

TASK: Select and rank the best articles for this user from the collected pool.

RULES:
1. Return EXACTLY the number of articles requested.
2. EVERY interest listed by the user MUST have at least 1-2 representative articles.
3. For 'Advanced' users: prioritize technical depth, market analysis, data.
4. For 'Beginner' users: prioritize accessible summaries and big-picture stories.
5. Assign 'matched_interest' — the user interest that BEST explains why this article was chosen.
6. Provide a brief 'reason' for each selection.

OUTPUT FORMAT — return valid JSON:
{
  "ranked_articles": [
    {
      "id": "article_temp_id",
      "matched_interest": "the user interest this serves",
      "relevance_score": 0.95,
      "reason": "why this article was selected"
    }
  ]
}
"""


def _parse_date(entry) -> Optional[datetime]:
    """Safely parse publish date from RSS entry."""
    try:
        if hasattr(entry, "published"):
            return dateparser.parse(entry.published)
    except Exception:
        pass
    return datetime.utcnow()


def _fetch_rss(query: str, max_articles: int = 8) -> list[dict]:
    """Fetch articles from Google News RSS for a keyword query."""
    url = GOOGLE_RSS_BASE + query.replace(" ", "+")
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries[:max_articles]:
        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "")
        link = getattr(entry, "link", "")

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
                "content": summary[:500] if summary else "",
                "url": link,
                "source": source,
                "date": str(_parse_date(entry)),
                "published": str(_parse_date(entry)),
                "query_used": query,
            })

    return articles


class ScrapingAgent:
    """Multi-interest RSS scraping agent with integrated LLM ranking.

    After scraping all interests, runs a final LLM ranking pass that:
    - Selects the top N articles by AI reasoning (not keyword math)
    - Assigns matched_interest via semantic understanding
    - Provides reason_for_selection for each article
    """

    def __init__(self, topic: str = "", interests: list[str] = None,
                 role: str = "student", level: str = "beginner"):
        self.topic = topic
        self.interests = interests or ([topic] if topic else [])
        self.role = role
        self.level = level
        self.saved_articles = []
        self.seen_urls = set()
        self.max_iterations = 2

    async def run(self) -> list[ArticleInput]:
        """Execute the agentic scraping loop + LLM final ranking."""
        print(f"🕵️ ScrapingAgent started")
        print(f"   Interests: {self.interests}")
        print(f"   Role: {self.role} | Level: {self.level}")

        # ── Phase 1: Scrape (multi-iteration) ─────────────────
        for iteration in range(self.max_iterations):
            print(f"🔄 Iteration {iteration+1}/{self.max_iterations}")

            queries = await self._generate_queries(iteration)

            new_articles = []
            for query in queries:
                print(f"🔍 Fetching RSS: {query}")
                scraped = _fetch_rss(query, max_articles=8)
                await asyncio.sleep(0.3)
                for art in scraped:
                    if art["url"] not in self.seen_urls:
                        self.seen_urls.add(art["url"])
                        new_articles.append(art)

            if new_articles:
                relevant_ids = await self._evaluate_relevance(new_articles)
                for art in new_articles:
                    if art["temp_id"] in relevant_ids:
                        self.saved_articles.append(art)

            print(f"   Kept {len(self.saved_articles)} total articles so far")

            if iteration < self.max_iterations - 1:
                has_gaps = await self._analyze_gaps()
                if not has_gaps:
                    print("✅ All interests covered. Stopping early.")
                    break
                else:
                    print("🔄 Gaps detected — running another iteration")
                    await asyncio.sleep(0.5)

        # ── Phase 2: LLM Final Ranking ────────────────────────
        if self.saved_articles:
            print(f"\n🧠 Running LLM final ranking on {len(self.saved_articles)} articles...")
            ranked = await self._llm_final_rank(top_n=15)
            print(f"🎯 LLM ranked {len(ranked)} articles")
        else:
            ranked = []

        # ── Convert to ArticleInput for compatibility ─────────
        final_list = []
        for art in ranked:
            final_list.append(ArticleInput(
                id=art.get("temp_id", str(uuid.uuid4())),
                title=art.get("title", "Untitled"),
                content=art.get("content", ""),
                url=art.get("url", ""),
                date=art.get("date", "Unknown"),
            ))

        print(f"🎯 Agent finished. Total articles: {len(final_list)}")
        return final_list

    def get_raw_articles(self) -> list[dict]:
        """Return raw article dicts (with query_used, source, etc.) for the orchestrator."""
        return self.saved_articles

    def get_ranked_articles(self) -> list[dict]:
        """Return the LLM-ranked articles with matched_interest and reason."""
        return self._ranked_result if hasattr(self, '_ranked_result') else self.saved_articles

    async def _llm_final_rank(self, top_n: int = 15) -> list[dict]:
        """LLM-based final ranking of all collected articles.

        This replaces TF-IDF ranking — the LLM assigns matched_interest
        and relevance_score using semantic understanding of the user's
        actual interests, not keyword overlap.
        """
        # Build article catalog (limit to 30 for prompt size)
        pool = self.saved_articles[:30]
        catalog = "\n".join([
            f"[{art['temp_id'][:8]}] {art['title']} | Source: {art.get('source', '?')}"
            for art in pool
        ])

        prompt = f"""USER PROFILE:
- Role: {self.role}
- Level: {self.level}
- Interests: {', '.join(self.interests)}

COLLECTED ARTICLES ({len(pool)}):
{catalog}

Select the TOP {top_n} most relevant articles for this user.
Ensure EVERY interest ({', '.join(self.interests)}) has at least 1-2 articles.
Use the article ID (first 8 chars in brackets) as the 'id' field."""

        try:
            result = await ask_llm_fast(RANKER_SYSTEM_PROMPT, prompt)
            ranked_list = result.get("ranked_articles", [])
        except Exception as e:
            logger.error(f"❌ LLM ranking in agent failed: {e}")
            self._ranked_result = pool[:top_n]
            return pool[:top_n]

        if not ranked_list:
            self._ranked_result = pool[:top_n]
            return pool[:top_n]

        # Map LLM results back to full article dicts
        id_lookup = {}
        for art in pool:
            fid = art["temp_id"]
            id_lookup[fid] = art
            id_lookup[fid[:8]] = art

        selected = []
        seen = set()

        for ranked in ranked_list[:top_n]:
            art_id = ranked.get("id", "")
            article = id_lookup.get(art_id)

            if not article:
                for key, val in id_lookup.items():
                    if art_id in key or key in art_id:
                        article = val
                        break

            if not article:
                continue

            url = article.get("url", "")
            if url in seen:
                continue
            seen.add(url)

            enriched = {
                **article,
                "matched_interest":     ranked.get("matched_interest", self.interests[0] if self.interests else ""),
                "relevance_score":      ranked.get("relevance_score", 0.8),
                "reason_for_selection": ranked.get("reason", ""),
            }
            selected.append(enriched)

        # Log distribution
        dist = {}
        for a in selected:
            mi = a.get("matched_interest", "?")
            dist[mi] = dist.get(mi, 0) + 1
        print(f"   Distribution: {dist}")

        self._ranked_result = selected
        return selected

    async def _generate_queries(self, iteration: int) -> list[str]:
        """Generate queries covering ALL user interests."""
        interests_str = ", ".join(self.interests) if self.interests else self.topic

        prompt = f"""User Interests: {interests_str}
Role: {self.role}
Iteration: {iteration}
Currently Saved Articles: {len(self.saved_articles)}

Generate search queries to cover ALL the listed interests.
Create 2-3 short keyword queries PER interest area."""

        if iteration == 0:
            prompt += "\nThis is the FIRST iteration. Generate broad queries for each interest."
        else:
            covered_queries = list(set(a.get("query_used", "") for a in self.saved_articles))
            prompt += f"\nQueries already used: {covered_queries}"
            prompt += "\nFocus on UNDERREPRESENTED interests and missing angles."

        res = await ask_llm_fast(AGENT_SYSTEM_PROMPT, prompt)
        queries = res.get("queries", [])

        validated = [q for q in queries if isinstance(q, str) and len(q.split()) <= 5]

        if not validated:
            validated = [f"{interest} India" for interest in self.interests[:5]]

        return validated

    async def _evaluate_relevance(self, articles: list[dict]) -> list[str]:
        """Evaluate which articles are relevant to the user's interests."""
        texts = "".join([
            f"ID: {a['temp_id']} | Title: {a['title']}\n"
            for a in articles
        ])
        prompt = f"""User Interests: {', '.join(self.interests)}
Role: {self.role}
Articles to evaluate:
{texts}

Return 'action': 'evaluate' and a list of 'kept_articles' IDs that closely match ANY of the user's interests."""

        res = await ask_llm_fast(AGENT_SYSTEM_PROMPT, prompt)
        return res.get("kept_articles", [])

    async def _analyze_gaps(self) -> bool:
        """Check if all interest areas are represented in saved articles."""
        if len(self.saved_articles) < 3:
            return True

        titles = [a["title"] for a in self.saved_articles]
        queries_used = list(set(a.get("query_used", "") for a in self.saved_articles))

        prompt = f"""User Interests: {', '.join(self.interests)}
Saved Article Titles ({len(titles)}):
{chr(10).join(f'- {t}' for t in titles)}

Queries used: {queries_used}

Are ANY interest areas completely MISSING from the collected articles?
Return action: analyze, gaps_found: true/false, and list any underrepresented interests."""

        res = await ask_llm_fast(AGENT_SYSTEM_PROMPT, prompt)
        return res.get("gaps_found", True)
