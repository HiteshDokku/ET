import httpx
import re
import base64
from bs4 import BeautifulSoup
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScrapedContent:
    text: str
    image_urls: list[str]


def _resolve_google_news_url(url: str) -> str:
    """Resolve a Google News redirect URL to the actual article destination.

    Google News RSS feeds return URLs like:
        https://news.google.com/rss/articles/CBMi...
    These pages rely on JavaScript to redirect, so BeautifulSoup cannot follow
    them.  We resolve the real URL via two strategies:
      1. Follow HTTP redirects (Google sometimes 302s to the real article).
      2. Decode the base64 payload embedded in the URL path as a fallback.
    """
    try:
        # Strategy 1: Follow redirects — Google often 302s to the final URL
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.head(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            final_url = str(resp.url)
            if "news.google.com" not in final_url:
                logger.info(f"Google News redirect resolved via HTTP: {final_url}")
                return final_url
    except Exception as exc:
        logger.debug(f"HTTP redirect resolution failed: {exc}")

    # Strategy 2: Decode the base64 article slug
    try:
        # The slug comes after /articles/ (e.g. CBMiXWh0dHBz…)
        match = re.search(r"/articles/([A-Za-z0-9_-]+)", url)
        if match:
            encoded = match.group(1)
            # Pad for base64
            padded = encoded + "=" * (-len(encoded) % 4)
            decoded_bytes = base64.urlsafe_b64decode(padded)
            # The decoded blob contains the target URL as a UTF-8 substring
            decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
            url_match = re.search(r"https?://[^\s\"<>]+", decoded_str)
            if url_match:
                resolved = url_match.group(0)
                logger.info(f"Google News URL decoded via base64: {resolved}")
                return resolved
    except Exception as exc:
        logger.debug(f"Base64 decode fallback failed: {exc}")

    # Strategy 3: Fetch the page and look for a meta-refresh or JS redirect hint
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            resp = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            # Look for a <meta http-equiv="refresh" content="...;url=..."> or
            # a window.location redirect in the body.
            body = resp.text
            meta_match = re.search(r'url=(https?://[^"\'>\s]+)', body, re.IGNORECASE)
            if meta_match:
                resolved = meta_match.group(1)
                logger.info(f"Google News URL resolved via meta-refresh: {resolved}")
                return resolved
            js_match = re.search(r'window\.location\s*=\s*["\']?(https?://[^"\';\s]+)', body)
            if js_match:
                resolved = js_match.group(1)
                logger.info(f"Google News URL resolved via JS redirect: {resolved}")
                return resolved
    except Exception as exc:
        logger.debug(f"Meta-refresh resolution failed: {exc}")

    logger.warning(f"Could not resolve Google News URL, using original: {url}")
    return url


def scrape_article(url: str) -> Optional[ScrapedContent]:
    """Scrapes paragraph text and high-quality image URLs from a news article."""
    if not url or not url.startswith("http"):
        return None

    # --- Resolve Google News redirect links ---
    if "news.google.com" in url:
        logger.info(f"Detected Google News URL, resolving redirect: {url}")
        url = _resolve_google_news_url(url)
        
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract text paragraphs
            paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3'])
            text_blocks = []
            for p in paragraphs:
                txt = p.get_text(separator=" ", strip=True)
                if len(txt) > 30:  # Skip tiny nav links or boilerplate
                    text_blocks.append(txt)
            
            full_text = "\n\n".join(text_blocks)
            
            # --- Guard: zero-content scrape ---
            if len(full_text) == 0:
                logger.warning(f"Scrape returned 0 characters for {url} — content extraction failed")
                return None
            
            # Extract images
            image_urls = []
            
            # 1. OpenGraph Image (usually highest quality hero image)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                if og_image["content"].startswith("http"):
                    image_urls.append(og_image["content"])
                
            # 2. Extract standard images scoring them on size/relevance
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-original")
                if not src or not src.startswith("http"):
                    continue
                    
                # Filter out obvious icons, logos, tracking pixels
                src_lower = src.lower()
                if any(bad in src_lower for bad in ["icon", "logo", "avatar", "svg", "spinner", "1x1", "tracking", "pixel", "scorecard", "analytics", "metrics", "adsystem", "banner"]):
                    continue
                    
                # Strict extension constraint for deep DOM traversal
                valid_exts = [".jpg", ".jpeg", ".png", ".webp", ".avif"]
                if not any(ext in src_lower for ext in valid_exts):
                    continue
                    
                image_urls.append(src)
            
            # Deduplicate preserving order
            unique_imgs = []
            for img in image_urls:
                if img not in unique_imgs:
                    unique_imgs.append(img)
                    
            logger.info(f"Scraped {len(full_text)} characters and {len(unique_imgs)} images from {url}")
            return ScrapedContent(text=full_text[:12000], image_urls=unique_imgs[:15])
            
    except Exception as e:
        logger.error(f"Failed to scrape article {url}: {e}")
        return None
