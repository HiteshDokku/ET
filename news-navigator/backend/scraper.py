import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def scrape_topic(query, max_articles=5):

    search_queries = [
        query,
        query + " India",
        query.split()[0]
    ]

    articles = []

    for q in search_queries:

        search_url = f"https://economictimes.indiatimes.com/searchresult.cms?query={quote(q)}"

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Timeout handling
        driver.set_page_load_timeout(15)

        try:
            driver.get(search_url)
        except:
            driver.execute_script("window.stop();")

        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, "html.parser")

        links = []

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if "/articleshow/" in href:

                if href.startswith("http"):
                    link = href
                else:
                    link = "https://economictimes.indiatimes.com" + href

                if link not in links:
                    links.append(link)

        # scrape articles
        for link in links[:max_articles]:

            article = scrape_article(link)

            if article:
                articles.append(article)

        if articles:
            break

    return articles


def scrape_article(url):

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("h1")

        if not title:
            return None

        title = title.text.strip()

        paragraphs = soup.find_all("p")

        content = " ".join([p.text.strip() for p in paragraphs])

        date = None

        time_tag = soup.find("time")

        if time_tag:
            date = time_tag.text.strip()

        return {
            "title": title,
            "content": content,
            "date": date,
            "source": "Economic Times",
            "url": url
        }

    except Exception as e:
        print("Error scraping article:", e)
        return None