import feedparser
import httpx
from datetime import datetime
from dateutil import parser as dateparser
from typing import List, Dict

"""
NEWS SERVICE — PREFERENCE-BASED FILTERING & RANKING

This service implements STRICT preference filtering:
- Only articles matching user interests are shown
- Articles are ranked by relevance score
- No generic/unrelated content in personalized feeds

FILTERING FLOW:
1. Fetch articles from all RSS feeds
2. Auto-detect categories/tags from content
3. Score each article against user interests (0.0 = no match)
4. FILTER OUT articles with 0.0 score
5. RANK remaining articles by score (highest first)
6. Return top N personalized articles

SCORING ALGORITHM:
- Base score: 0.0 (no match = filtered out)
- +0.5 per matching interest tag
- +0.15 per tag × engagement history
- +0.2 bonus for multiple matching tags
- Max: 1.0

Example:
- User interests: ["AI", "startups"]
- Article tags: ["AI", "tech news"]
  → Match: ["AI"] → Score: 0.5 + engagement bonus
- Article tags: ["politics", "elections"]
  → Match: [] → Score: 0.0 → FILTERED OUT
"""
ET_RSS_FEEDS = {
    "markets":  "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "tech":     "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "startups": "https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/7800734.cms",
    "finance":  "https://economictimes.indiatimes.com/wealth/rssfeeds/837555174.cms",
    "general":  "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
}

# ─── Category → keywords mapping (for auto-tagging articles) ──
CATEGORY_KEYWORDS = {
    "AI":        ["artificial intelligence", "AI", "machine learning", "LLM", "ChatGPT", "deepmind"],
    "startups":  ["startup", "funding", "series A", "series B", "unicorn", "VC", "venture"],
    "markets":   ["stocks", "market", "sensex", "nifty", "BSE", "NSE", "equity", "shares"],
    "crypto":    ["bitcoin", "crypto", "blockchain", "ethereum", "web3"],
    "finance":   ["RBI", "interest rate", "inflation", "GDP", "budget", "economy"],
    "tech":      ["technology", "software", "SaaS", "cloud", "cybersecurity"],
    "policy":    ["government", "regulation", "SEBI", "policy", "ministry"],
}


def detect_categories(title: str, summary: str) -> List[str]:
    """
    Auto-detect categories from article title + summary using keywords.
    Returns a list like ["AI", "startups"] or ["markets", "finance"]
    """
    text = (title + " " + (summary or "")).lower()
    found = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            found.append(category)
    return found if found else ["general"]


def parse_date(entry) -> datetime:
    """Safely parse publish date from RSS feed entry."""
    try:
        if hasattr(entry, "published"):
            return dateparser.parse(entry.published)
    except Exception:
        pass
    return datetime.utcnow()


async def fetch_all_feeds() -> List[Dict]:
    """
    Fetch articles from all ET RSS feeds.
    Returns a list of article dicts ready to store in DB / Redis.
    """
    all_articles = []

    for feed_name, feed_url in ET_RSS_FEEDS.items():
        try:
            # feedparser handles RSS parsing
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:15]:   # max 15 articles per feed
                article = {
                    "title":     getattr(entry, "title", ""),
                    "summary":   getattr(entry, "summary", ""),
                    "url":       getattr(entry, "link", ""),
                    "source":    f"ET {feed_name.capitalize()}",
                    "category":  feed_name,
                    "tags":      detect_categories(
                                    getattr(entry, "title", ""),
                                    getattr(entry, "summary", "")
                                 ),
                    "published": parse_date(entry),
                }

                # Only add if it has a title and URL
                if article["title"] and article["url"]:
                    all_articles.append(article)

        except Exception as e:
            # Don't crash if one feed fails — just skip it
            print(f"⚠️  Failed to fetch {feed_name} feed: {e}")
            continue

    print(f"✅  Fetched {len(all_articles)} articles from ET RSS feeds")
    return all_articles


def score_article_for_user(article: Dict, profile: Dict) -> float:
    """
    Score how relevant an article is for a specific user (0.0 to 1.0).
    
    TWO-TIER FILTERING:
    1. PRIMARY: Match user interests against article tags
    2. FALLBACK: If no strict matches, match against article category
    
    Scoring logic:
    - Strict match (interest ↔ tag): +0.8
    - Category match (interest ↔ category): +0.5
    - Engagement bonus: +0.2 per tag
    - Multiple matches bonus: +0.1
    """
    user_interests = [i.lower() for i in profile.get("interests", [])]
    user_engagement = profile.get("engagement", {})
    article_tags = [t.lower() for t in article.get("tags", [])]
    article_category = article.get("category", "").lower()
    
    # Debug logging
    print(f"📌 Scoring article: tags={article_tags}, category={article_category}")
    print(f"👤 User interests: {user_interests}")
    
    # If user has NO interests set, show everything (fallback)
    if not user_interests:
        print("⚠️  User has no interests set - showing all articles (fallback mode)")
        return 0.5  # neutral score for unfiltered users
    
    # TIER 1: Check for strict tag matches (user interest appears in article tags)
    matching_tags = set(user_interests) & set(article_tags)
    if matching_tags:
        print(f"✅ Strict tag match found: {matching_tags}")
        score = 0.8
        
        # Engagement bonus
        for tag in matching_tags:
            engagement_score = user_engagement.get(tag, 0.5)
            score += engagement_score * 0.1
        
        # Multiple matches bonus
        if len(matching_tags) > 1:
            score += 0.1
        
        return min(1.0, score)
    
    # TIER 2: Check for category match (user interest appears in article category)
    matching_categories = set(user_interests) & {article_category}
    if matching_categories:
        print(f"✅ Category match found: {matching_categories}")
        score = 0.5
        
        # Engagement bonus
        for cat in matching_categories:
            engagement_score = user_engagement.get(cat, 0.5)
            score += engagement_score * 0.1
        
        return min(1.0, score)
    
    # TIER 3: Keyword-based fallback (check if any user interest keywords appear in article)
    article_text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    for interest in user_interests:
        if interest in article_text:
            print(f"✅ Keyword match found: '{interest}' in article text")
            return 0.6
    
    # No match
    print(f"❌ No match - article excluded")
    return 0.0


def rank_articles_for_user(articles: List[Dict], profile: Dict, top_n: int = 10) -> List[Dict]:
    """
    STRICT filtering:
    - Only strong matches are allowed
    - Weak matches are NOT included unless absolutely necessary
    """
    scored = []
    
    for article in articles:
        score = score_article_for_user(article, profile)
        if score > 0.0:
            scored.append({
                **article,
                "relevance_score": round(score, 3)
            })
    
    # Sort by score descending
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # ✅ STEP 1: Keep ONLY strong matches
    filtered = [a for a in scored if a["relevance_score"] >= 0.6]
    
    # ✅ STEP 2: Fallback ONLY if nothing found
    if not filtered:
        print("⚠️ No strong matches, relaxing threshold to 0.4")
        filtered = [a for a in scored if a["relevance_score"] >= 0.4]
    
    # Final sort (important after filtering)
    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    print(f"🎯 Filtered: {len(filtered)} relevant / {len(articles)} total articles")
    if filtered:
        print(f"   Score range: {filtered[-1]['relevance_score']:.2f} - {filtered[0]['relevance_score']:.2f}")
    
    return filtered[:top_n]