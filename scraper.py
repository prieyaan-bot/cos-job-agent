import requests
import json
import time
import random
from datetime import datetime, timezone
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

SF_BAY_AREA_TERMS = [
    "san francisco", "sf", "bay area", "silicon valley",
    "san jose", "palo alto", "mountain view", "sunnyvale",
    "menlo park", "redwood city", "foster city", "south san francisco",
    "oakland", "berkeley", "santa clara", "cupertino", "remote"
]

GREENHOUSE_COMPANIES = [
    "stripe", "openai", "notion", "figma", "airtable", "brex",
    "rippling", "gusto", "chime", "robinhood", "coinbase", "databricks",
    "scale", "together", "anthropic", "asana", "dropbox", "lyft",
    "doordash", "instacart", "airbnb", "pinterest", "reddit",
    "palantir", "plaid", "carta", "lattice", "retool", "linear",
    "vercel", "loom", "mercury", "ramp", "deel", "remote",
    "watershed", "benchling", "amplitude", "mixpanel", "segment",
    "twilio", "okta", "cloudflare", "fastly", "hashicorp",
]

LEVER_COMPANIES = [
    "netflix", "spotify", "medium", "coda", "miro",
    "grammarly", "duolingo", "canva", "hubspot", "zendesk",
    "intercom", "freshworks", "clickup", "gitlab",
    "pagerduty", "datadog", "newrelic", "elastic", "confluent",
    "dbt-labs", "fivetran", "hightouch", "census",
]


def random_delay(min_s=1.5, max_s=4.0):
    time.sleep(random.uniform(min_s, max_s))


def _is_cos_role(title: str) -> bool:
    cos_keywords = [
        "chief of staff",
        "chief-of-staff",
        "cos to",
        "cos,",
    ]
    return any(kw in title for kw in cos_keywords)


def _is_bay_area(location: str) -> bool:
    if not location:
        return False
    location = location.lower()
    return any(term in location for term in SF_BAY_AREA_TERMS)


def _extract_gh_description(job: dict) -> str:
    content = job.get("content", "") or ""
    soup = BeautifulSoup(content, "html.parser")
    return soup.get_text(separator=" ").strip()[:3000]


def _extract_lever_description(post: dict) -> str:
    lists = post.get("lists", [])
    text_parts = []
    for lst in lists:
        content = lst.get("content", "")
        soup = BeautifulSoup(content, "html.parser")
        text_parts.append(soup.get_text(separator=" "))
    additional = post.get("additional", "")
    if additional:
        soup = BeautifulSoup(additional, "html.parser")
        text_parts.append(soup.get_text(separator=" "))
    return " ".join(text_parts).strip()[:3000]


def _extract_company_from_indeed(title: str) -> str:
    parts = title.split(" - ")
    return parts[-1].strip() if len(parts) > 1 else "Unknown"


def scrape_greenhouse() -> list[dict]:
    jobs = []
    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for job in data.get("jobs", []):
                title = job.get("title", "").lower()
                location = job.get("location", {}).get("name", "").lower()
                if not _is_cos_role(title):
                    continue
                if not _is_bay_area(location):
                    continue
                jobs.append({
                    "source": "Greenhouse",
                    "company": company.capitalize(),
                    "title": job.get("title"),
                    "location": job.get("location", {}).get("name"),
                    "url": job.get("absolute_url"),
                    "job_id": str(job.get("id")),
                    "description": _extract_gh_description(job),
                    "posted_at": job.get("updated_at"),
                    "ats": "greenhouse",
                })
            random_delay(0.5, 1.5)
        except Exception as e:
            print(f"[Greenhouse] Error for {company}: {e}")
    return jobs


def scrape_lever() -> list[dict]:
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            postings = resp.json()
            for post in postings:
                title = post.get("text", "").lower()
                location = post.get("categories", {}).get("location", "").lower()
                if not _is_cos_role(title):
                    continue
                if not _is_bay_area(location):
                    continue
                jobs.append({
                    "source": "Lever",
                    "company": company.capitalize(),
                    "title": post.get("text"),
                    "location": post.get("categories", {}).get("location"),
                    "url": post.get("hostedUrl"),
                    "job_id": post.get("id"),
                    "description": _extract_lever_description(post),
                    "posted_at": datetime.fromtimestamp(
                        post.get("createdAt", 0) / 1000, tz=timezone.utc
                    ).isoformat(),
                    "ats": "lever",
                })
            random_delay(0.5, 1.5)
        except Exception as e:
            print(f"[Lever] Error for {company}: {e}")
    return jobs


def scrape_indeed() -> list[dict]:
    jobs = []
    for keyword in ["chief+of+staff", "chief+of+staff+operations"]:
        try:
            url = (
                f"https://www.indeed.com/rss?q={keyword}"
                f"&l=San+Francisco+Bay+Area%2C+CA&radius=25&sort=date"
            )
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").get_text() if item.find("title") else ""
                link = item.find("link").get_text() if item.find("link") else ""
                description = item.find("description").get_text() if item.find("description") else ""
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                if not _is_cos_role(title.lower()):
                    continue
                jobs.append({
                    "source": "Indeed",
                    "company": _extract_company_from_indeed(title),
                    "title": title.split(" - ")[0].strip() if " - " in title else title,
                    "location": "San Francisco Bay Area, CA",
                    "url": link,
                    "job_id": link.split("jk=")[-1].split("&")[0] if "jk=" in link else link[-20:],
                    "description": BeautifulSoup(description, "html.parser").get_text()[:3000],
                    "posted_at": pub_date,
                    "ats": "indeed",
                })
            random_delay(2, 4)
        except Exception as e:
            print(f"[Indeed] Error: {e}")
    return jobs


def scrape_wellfound() -> list[dict]:
    jobs = []
    try:
        url = "https://wellfound.com/role/l/chief-of-staff/san-francisco-bay-area"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, "html.parser")
        job_cards = soup.find_all("div", {"data-test": "StartupResult"})
        for card in job_cards:
            title_el = card.find("a", {"data-test": "job-title"})
            company_el = card.find("a", {"data-test": "startup-link"})
            if not title_el:
                continue
            title = title_el.get_text().strip()
            if not _is_cos_role(title.lower()):
                continue
            jobs.append({
                "source": "Wellfound",
                "company": company_el.get_text().strip() if company_el else "Unknown",
                "title": title,
                "location": "San Francisco Bay Area",
                "url": "https://wellfound.com" + title_el.get("href", ""),
                "job_id": title_el.get("href", "")[-20:],
                "description": "",
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "ats": "wellfound",
            })
    except Exception as e:
        print(f"[Wellfound] Error: {e}")
    return jobs


def scrape_all_boards() -> list[dict]:
    print("🔍 Scraping Greenhouse...")
    gh_jobs = scrape_greenhouse()
    print(f"   Found {len(gh_jobs)} jobs")

    print("🔍 Scraping Lever...")
    lever_jobs = scrape_lever()
    print(f"   Found {len(lever_jobs)} jobs")

    print("🔍 Scraping Indeed...")
    indeed_jobs = scrape_indeed()
    print(f"   Found {len(indeed_jobs)} jobs")

    print("🔍 Scraping Wellfound...")
    wf_jobs = scrape_wellfound()
    print(f"   Found {len(wf_jobs)} jobs")

    all_jobs = gh_jobs + lever_jobs + indeed_jobs + wf_jobs
    print(f"\n✅ Total raw jobs found: {len(all_jobs)}")
    return all_jobs
