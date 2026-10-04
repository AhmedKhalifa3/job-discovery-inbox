#!/usr/bin/env python3
"""Job Scout: Autonomous Job Discovery Engine for Ahmed Khalifa.

Scrapes ATS systems (Personio, Ashby, Greenhouse, Lever) and tech job APIs
for recent postings, scores them against candidate criteria, and syncs
with Notion & Overleaf pipeline.
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

from dotenv import load_dotenv
load_dotenv()

from config import (
    SEARCH_QUERIES,
    API_SOURCES,
    ACTIVE_PROFILE,
    DOMAIN_BLACKLIST
)
from notion_sync import NotionJobSyncer

SEEN_JOBS_FILE = "seen_jobs.json"
OUTPUT_JSON_FILE = "discovered_jobs.json"
OUTPUT_MD_FILE = "discovered_jobs.md"

def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_urls: set):
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_urls), f, indent=2)

def is_valid_job_url(url: str) -> bool:
    if not url:
        return False
    lower_url = url.lower()
    if any(ad in lower_url for ad in ['/aclick', '/aclk', 'ad_id=', 'msclkid=']):
        return False
    for bad_domain in DOMAIN_BLACKLIST:
        if bad_domain in lower_url:
            return False
    return True

class ProfileScorer:
    """Evaluates and scores job opportunities dynamically based on a candidate's profile."""

    def __init__(self, profile: Optional[Dict[str, Any]] = None):
        prof = profile or ACTIVE_PROFILE
        self.target_roles = [r.lower() for r in prof.get("target_roles", [])]
        self.skills = [s.lower() for s in prof.get("skills", [])]
        self.contract_types = [c.lower() for c in prof.get("contract_types", [])]
        self.negative_keywords = [n.lower() for n in prof.get("negative_keywords", [])]
        self.negative_title_keywords = [nt.lower() for nt in prof.get("negative_title_keywords", [])]
        self.locations = [l.lower() for l in prof.get("locations", [])]

    def score(self, title: str, snippet: str, location: str = "", url: str = "") -> int:
        if not is_valid_job_url(url):
            return -10

        lower_title = title.lower()
        text = f"{title} {snippet} {location}".lower()

        # 1. Profile Title-Only Exclusions (Disqualify if keyword appears in job title)
        for blocker in self.negative_title_keywords:
            if blocker in lower_title:
                return -10

        # 2. Profile General Negative Exclusions (Disqualify if in title or text)
        for neg in self.negative_keywords:
            if neg in lower_title or neg in text:
                return -10

        score = 0

        # 3. Target Role & Skill Matching from Profile
        matched_role = False
        for role in self.target_roles:
            if role in lower_title:
                matched_role = True
                score += 3  # Higher boost for matching target title directly
                break
            elif role in text:
                matched_role = True
                score += 1
                break

        matched_skill = False
        for skill in self.skills:
            if skill in lower_title:
                matched_skill = True
                score += 2
            elif skill in text:
                matched_skill = True
                score += 1

        # Must match at least one target role or skill to be considered relevant
        if not (matched_role or matched_skill):
            return 0

        # 4. Preferred Contract / Seniority Types Boost (from profile)
        if self.contract_types and any(ct in lower_title for ct in self.contract_types):
            score += 2

        # 5. Preferred Locations Boost (from profile)
        if self.locations and any(loc in text for loc in self.locations):
            score += 2

        return score

DEFAULT_SCORER = ProfileScorer(ACTIVE_PROFILE)

def score_job(
    title: str,
    snippet: str,
    location: str = "",
    url: str = "",
    scorer: Optional[ProfileScorer] = None
) -> int:
    active_scorer = scorer or DEFAULT_SCORER
    return active_scorer.score(title, snippet, location, url)

def extract_company_from_title(title: str, url: str) -> str:
    # Common formats: "Role at Company", "Company - Role", "Role | Company"
    if " at " in title:
        parts = title.split(" at ")
        return parts[-1].strip()
    if " | " in title:
        parts = title.split(" | ")
        return parts[-1].strip()
    if " - " in title:
        parts = title.split(" - ")
        return parts[0].strip()

    # Fallback: extract domain / subdomain
    match = re.search(r"https?://([^/]+)/", url)
    if match:
        domain = match.group(1)
        sub = domain.split(".")[0]
        if sub not in ("boards", "jobs", "www"):
            return sub.capitalize()
    return "Company"

def clean_role_title(title: str) -> str:
    # Strip trailing website names like " | Greenhouse", " - Lever"
    cleaned = re.sub(r"\s*(\||-|–)\s*(Greenhouse|Lever|Ashby|Personio|Jobs|Careers).*$", "", title, flags=re.IGNORECASE)
    return cleaned.strip()

def search_duckduckgo(query: str, timelimit: str = "w", max_results: int = 15) -> List[Dict[str, Any]]:
    """Runs dork query using duckduckgo_search."""
    jobs = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = ddgs.text(query, timelimit=timelimit, max_results=max_results)
            for r in results:
                title = r.get("title", "")
                url = r.get("href", "")
                body = r.get("body", "")

                role = clean_role_title(title)
                company = extract_company_from_title(title, url)

                jobs.append({
                    "company": company,
                    "role": role,
                    "url": url,
                    "snippet": body,
                    "location": "Remote / Specified in JD",
                    "source": "Search Dork"
                })
    except ImportError:
        print("[Warning] duckduckgo_search not installed. Run: pip install duckduckgo_search")
    except Exception as e:
        print(f"[Warning] Search error on query '{query[:40]}...': {e}")
    return jobs

def fetch_arbeitnow_jobs() -> List[Dict[str, Any]]:
    """Fetches English-speaking Germany tech jobs from Arbeitnow."""
    jobs = []
    try:
        import requests
        res = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=10)
        if res.status_code == 200:
            data = res.json().get("data", [])
            for item in data:
                title = item.get("title", "")
                description = item.get("description", "")
                tags = " ".join(item.get("tags", []))
                snippet = f"{description[:300]} Tags: {tags}"

                loc = item.get("location", "Germany")
                if item.get("remote"):
                    loc = f"{loc} (Remote)"

                jobs.append({
                    "company": item.get("company_name", "Unknown"),
                    "role": title,
                    "url": item.get("url", ""),
                    "snippet": snippet,
                    "location": loc,
                    "source": "Arbeitnow API"
                })
    except Exception as e:
        print(f"[Warning] Failed to fetch Arbeitnow: {e}")
    return jobs

def fetch_jobicy_jobs() -> List[Dict[str, Any]]:
    """Fetches remote engineering jobs from Jobicy."""
    jobs = []
    try:
        import requests
        url = "https://jobicy.com/api/v2/remote-jobs?count=30&industry=engineering"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json().get("jobs", [])
            for item in data:
                jobs.append({
                    "company": item.get("companyName", "Unknown"),
                    "role": item.get("jobTitle", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("jobExcerpt", ""),
                    "location": item.get("jobGeo", "Remote"),
                    "source": "Jobicy API"
                })
    except Exception as e:
        print(f"[Warning] Failed to fetch Jobicy: {e}")
    return jobs

def generate_markdown_report(jobs: List[Dict[str, Any]]) -> str:
    lines = [
        f"# 🎯 Discovered Job Opportunities ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        f"Total fresh matching roles: **{len(jobs)}**\n",
        "| Score | Role | Company | Location | Source | Link |",
        "| :---: | :--- | :--- | :--- | :--- | :--- |"
    ]
    for j in jobs:
        score = j.get("score", 0)
        badge = "🔥 High" if score >= 4 else "⭐ Med"
        link = f"[Apply / View]({j['url']})" if j.get("url") else "N/A"
        role = j['role'].replace('|', '/')
        company = j['company'].replace('|', '/')
        loc = j['location'].replace('|', '/')
        lines.append(f"| {badge} ({score}) | **{role}** | {company} | {loc} | {j['source']} | {link} |")

    lines.append("\n---\n")
    lines.append("### Recommended Next Steps:\n")
    lines.append("1. **Wishlist Sync:** Jobs have been added/queued for your Notion Tracker.")
    lines.append("2. **CV Tailoring:** Pick top target roles and invoke Overleaf CV Agent to compile tailored resumes.")
    lines.append("3. **Apply:** Submit application and track status.")
    return "\n".join(lines)

def run_scout(
    categories: List[str],
    timelimit: str = "w",
    push_to_notion: bool = False,
    include_apis: bool = True,
    profile_data: Optional[Dict[str, Any]] = None,
    queries_dict: Optional[Dict[str, List[str]]] = None
):
    print(f"\n🚀 Running Job Scout for categories: {', '.join(categories)}")
    print(f"⏱️  Time filter: {'Past 24 hours' if timelimit == 'd' else 'Past week'}")

    scorer = ProfileScorer(profile_data)
    active_queries = queries_dict or SEARCH_QUERIES

    seen_urls = load_seen_jobs()
    discovered_jobs: List[Dict[str, Any]] = []

    # 1. Search Dorks
    for cat in categories:
        queries = active_queries.get(cat, [])
        for q in queries:
            print(f"🔎 Scanning: {q[:70]}...")
            raw_results = search_duckduckgo(q, timelimit=timelimit)
            for r in raw_results:
                url = r.get("url", "")
                if url in seen_urls:
                    continue

                score = score_job(r["role"], r["snippet"], r["location"], url=url, scorer=scorer)
                if score >= 1:
                    r["score"] = score
                    r["category"] = cat
                    discovered_jobs.append(r)
                    seen_urls.add(url)

    # 2. Free Job APIs (Arbeitnow & Jobicy)
    if include_apis:
        print("\n🌐 Querying direct tech job feeds (Germany & Remote Europe)...")
        api_jobs = fetch_arbeitnow_jobs() + fetch_jobicy_jobs()
        for r in api_jobs:
            url = r.get("url", "")
            if url in seen_urls:
                continue

            score = score_job(r["role"], r["snippet"], r["location"], url=url, scorer=scorer)
            if score >= 1:
                r["score"] = score
                r["category"] = "api_feed"
                discovered_jobs.append(r)
                seen_urls.add(url)

    # Sort descending by match score
    discovered_jobs.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Save outputs
    save_seen_jobs(seen_urls)

    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(discovered_jobs, f, indent=2)

    md_report = generate_markdown_report(discovered_jobs)
    with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"\n✅ Finished! Found {len(discovered_jobs)} matching postings.")
    print(f"📁 Saved results to '{OUTPUT_JSON_FILE}' and '{OUTPUT_MD_FILE}'.")

    # 3. Notion Sync (optional or automated)
    if push_to_notion and discovered_jobs:
        print("\n📤 Pushing matches to Notion Database (as 'Wishlist')...")
        syncer = NotionJobSyncer()
        if syncer.is_configured():
            pushed_count = 0
            for job in discovered_jobs:
                if syncer.push_job(job):
                    pushed_count += 1
            print(f"🎉 Successfully logged {pushed_count} jobs to Notion!")
        else:
            print("[Info] Notion credentials not configured in .env. Skipping sync.")

    return discovered_jobs

def main():
    parser = argparse.ArgumentParser(description="Autonomous Job Discovery Scout")
    parser.add_argument(
        "--profile",
        default=None,
        help="Path to custom candidate profile YAML/JSON file (default: profile.yaml or profile.example.yaml)"
    )
    parser.add_argument(
        "--category",
        default="all",
        help="Category of roles to scout (default: all)"
    )
    parser.add_argument(
        "--fresh",
        choices=["24h", "week", "any"],
        default="week",
        help="Freshness window (24h, week, or any)"
    )
    parser.add_argument(
        "--push-notion",
        action="store_true",
        help="Push found jobs directly to Notion Database"
    )
    parser.add_argument(
        "--no-apis",
        action="store_true",
        help="Disable direct API feeds (search dorks only)"
    )

    args = parser.parse_args()
    if args.fresh == "24h":
        timelimit = "d"
    elif args.fresh == "week":
        timelimit = "w"
    else:
        timelimit = None

    if args.profile:
        from config import load_profile, generate_search_dorks
        profile_data = load_profile(args.profile)
        queries = generate_search_dorks(profile_data)
    else:
        profile_data = ACTIVE_PROFILE
        queries = SEARCH_QUERIES

    if args.category == "all":
        categories = list(queries.keys())
    else:
        categories = [args.category]

    run_scout(
        categories=categories,
        timelimit=timelimit,
        push_to_notion=args.push_notion,
        include_apis=not args.no_apis,
        profile_data=profile_data,
        queries_dict=queries
    )

if __name__ == "__main__":
    main()
