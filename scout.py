#!/usr/bin/env python3
"""Job Scout: Autonomous Job Discovery Engine for Ahmed Khalifa.

Scrapes ATS systems (Personio, Ashby, Greenhouse, Lever) and tech job APIs
for recent postings, scores them against candidate criteria, and syncs
with Notion & Overleaf pipeline.
"""

import os
import sys
import time
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
    DOMAIN_BLACKLIST,
    ATS_DOMAINS,
    resolve_allowed_domains,
    resolve_blocked_domains
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

def is_valid_job_url(
    url: str,
    is_dork: bool = False,
    custom_domains: Optional[List[str]] = None,
    allowed_domains: Optional[List[str]] = None,
    blocked_domains: Optional[List[str]] = None
) -> bool:
    if not url:
        return False
    lower_url = url.lower()
    if any(ad in lower_url for ad in ['/aclick', '/aclk', 'ad_id=', 'msclkid=']):
        return False

    effective_blacklist = blocked_domains if blocked_domains is not None else DOMAIN_BLACKLIST
    for bad_domain in effective_blacklist:
        if bad_domain in lower_url:
            return False

    if is_dork:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower().strip('/')

        effective_allowed = set(ATS_DOMAINS)
        if allowed_domains:
            effective_allowed.update(d.lower() for d in allowed_domains)
        if custom_domains:
            effective_allowed.update(d.lower() for d in custom_domains)

        if not any(d in host for d in effective_allowed):
            return False

        # Generic reject for bare landing/nav/info pages
        parts = [p for p in path.split('/') if p]
        if not path or path in ('careers', 'jobs', 'about', 'search', 'faq', 'magazin', 'events', 'standorte', 'rechtliches', 'alumni', 'karriereservice'):
            return False
        if any(bad in parts for bad in ('magazin', 'faq', 'standorte', 'rechtliches', 'students', 'account', 'merkzettel', 'ki', 'karriereservice', 'alumni', 'events')):
            return False

        # Social networks (X / Twitter) check
        if any(xd in host for xd in ('x.com', 'twitter.com')):
            if not any(marker in lower_url for marker in ('/status/', '/jobs/', '/article/')):
                return False
            if parts and parts[0] in ('home', 'explore', 'login', 'notifications', 'search', 'settings', 'hashtag'):
                return False

    return True

LANGUAGE_DICTIONARY = {
    "german": {
        "names": ["german", "deutsch", "deutsche", "deutschen"],
        "native_patterns": [
            r"flie[ßs]end\w*\s+(auf\s+|in\s+)?deutsch\w*",
            r"deutsch\w*\s+(in\s+wort\s+und\s+schrift|erforderlich|vorausgesetzt|zwingend|notwendig)",
            r"(sehr\s+gute|gute|verhandlungssicher\w*)\s+deutsch\w*",
            r"sicher\s+(auf|in)\s+deutsch\w*",
            r"verhandlungssicher\w*\s+(auf|in)?\s*deutsch\w*",
            r"deutsch\s*[:\-\(\s]*(c1|c2|b2|verhandlungssicher|flie[ßs]end)",
            r"(c1|c2|b2)\s*(-|\s)?deutsch\w*",
            r"deutschkenntnisse",
            r"deutsch\s+auf\s+(b2|c1|c2)",
            r"muttersprache\s+deutsch\w*",
            r"hervorragende\s+deutschkenntnisse",
        ]
    },
    "french": {
        "names": ["french", "français", "francais"],
        "native_patterns": [
            r"fran[çc]ais\s+(courant|bilingue|exig[ée]|requis|indispensable|langue\s+maternelle)",
            r"ma[îi]trise\s+(parfaite\s+)?du\s+fran[çc]ais",
            r"(niveau\s+)?(c1|c2)\s+en\s+fran[çc]ais",
            r"parler\s+couramment\s+fran[çc]ais",
            r"langue\s+de\s+travail\s*:\s*fran[çc]ais",
        ]
    },
    "spanish": {
        "names": ["spanish", "español", "espanol", "castellano"],
        "native_patterns": [
            r"espa[ñn]ol\s+(fluido|avanzado|nativo|requerido|imprescindible|obligatorio)",
            r"dominio\s+(del\s+)?espa[ñn]ol",
            r"(nivel\s+)?(c1|c2)\s+de\s+espa[ñn]ol",
            r"hablar\s+espa[ñn]ol\s+con\s+fluidez",
        ]
    },
    "italian": {
        "names": ["italian", "italiano"],
        "native_patterns": [
            r"italiano\s+(fluente|madrelingua|richiesto|indispensabile|avanzato)",
            r"ottima\s+conoscenza\s+dell['’]italiano",
            r"(livello\s+)?(c1|c2)\s+(di|in)\s+italiano",
        ]
    },
    "dutch": {
        "names": ["dutch", "nederlands"],
        "native_patterns": [
            r"nederlands\s+(vloeiend|moedertaal|vereist|noodzakelijk)",
            r"uitstekende\s+beheersing\s+van\s+de\s+nederlandse\s+taal",
            r"vloeiend\s+nederlands",
            r"beheersing\s+van\s+het\s+nederlands",
        ]
    },
    "portuguese": {
        "names": ["portuguese", "português", "portugues"],
        "native_patterns": [
            r"portugu[êe]s\s+(fluente|nativo|obrigat[óo]rio|avan[çc]ado)",
            r"dom[íi]nio\s+(do\s+)?portugu[êe]s",
        ]
    },
    "polish": {
        "names": ["polish", "polski"],
        "native_patterns": [
            r"j[ęe]zyk\s+polski\s+(bieg[łl]y|wymagany|ojczysty)",
            r"bieg[łl]a\s+znajomo[ść]\s+j[ęe]zyka\s+polskiego",
        ]
    },
    "swedish": {
        "names": ["swedish", "svenska"],
        "native_patterns": [
            r"svenska\s+(flytande|modersm[åa]l|krav)",
            r"flytande\s+svenska",
        ]
    }
}

def build_language_filter(excluded_languages: List[str]):
    """Dynamically compiles requirement patterns and exemption phrases for excluded languages.

    Supports native patterns for known languages plus international English patterns
    (fluent, mandatory, C1/C2) for ANY language name provided in candidate profile.
    """
    if not excluded_languages:
        return None, []

    patterns = []
    exemptions = []

    for lang in excluded_languages:
        lang_key = lang.strip().lower()
        if not lang_key:
            continue

        known = LANGUAGE_DICTIONARY.get(lang_key)
        if known:
            patterns.extend(known.get("native_patterns", []))
            names = known.get("names", [lang_key])
        else:
            names = [lang_key]

        # International English phrasing patterns for this language
        for name in names:
            escaped_name = re.escape(name)
            patterns.append(rf"\b(fluent|native|business\s+fluent|proficient)\s+(in\s+)?{escaped_name}\b")
            patterns.append(rf"\b{escaped_name}\s+(is\s+)?(mandatory|essential|required|indispensable|compulsory|prerequisite)\b")
            patterns.append(rf"\b{escaped_name}\s*[:\-\(\s]*(c1|c2|fluent|native|b2|advanced)\b")
            patterns.append(rf"\b(c1|c2|b2)\s*(-|\s)?{escaped_name}\b")
            patterns.append(rf"\b(minimum|level)\s+(c1|c2|b2)\s+(in\s+)?{escaped_name}\b")
            patterns.append(rf"\bexcellent\s+(command\s+of\s+)?{escaped_name}\b")
            patterns.append(rf"\bmust\s+(speak|be\s+fluent\s+in)\s+{escaped_name}\b")
            patterns.append(rf"\b{escaped_name}\s+at\s+a\s+(c1|c2|b2|fluent)\s+level\b")

            # Exemptions where language is mentioned but NOT mandatory
            exemptions.extend([
                f"no {name}",
                f"{name} not required",
                f"not required to speak {name}",
                f"{name} is a plus",
                f"{name} is an advantage",
                f"{name} is beneficial",
                f"{name} is optional",
                f"bonus: {name}",
                f"bonus: fluent {name}",
                f"{name} a plus"
            ])

    if not patterns:
        return None, []

    compiled_regex = re.compile("|".join(patterns), re.IGNORECASE)
    return compiled_regex, exemptions

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
        # Expanded locations: If candidate targets Germany, automatically recognize all major German cities & states
        self.expanded_locations = set(self.locations)
        if any(g in self.locations for g in ("germany", "deutschland", "de")):
            self.expanded_locations.update({
                "berlin", "münchen", "munich", "hamburg", "frankfurt", "köln", "cologne",
                "stuttgart", "düsseldorf", "dusseldorf", "leipzig", "dresden", "karlsruhe",
                "nürnberg", "nuremberg", "erlangen", "hannover", "hanover", "bonn",
                "mannheim", "heidelberg", "darmstadt", "aachen", "bremen", "freiburg",
                "regensburg", "ingolstadt", "ulm", "augsburg", "würzburg", "wuerzburg",
                "bayern", "bavaria", "baden-württemberg", "nrw", "hessen"
            })
        # Identify immediate home/priority cities (defaults to top 4 specific entries in locations)
        self.home_cities = [c.lower() for c in prof.get("home_cities", [])]
        if not self.home_cities:
            general_keys = {"germany", "deutschland", "remote", "europe", "remote germany", "united states", "bayern", "bavaria"}
            candidate_specifics = [l.lower() for l in self.locations if l.lower() not in general_keys]
            self.home_cities = candidate_specifics[:4]

        self.excluded_languages = list(prof.get("excluded_language_requirements", []))
        if prof.get("exclude_german_required") and "German" not in self.excluded_languages and "german" not in [l.lower() for l in self.excluded_languages]:
            self.excluded_languages.append("German")
        self.language_regex, self.language_exemptions = build_language_filter(self.excluded_languages)

        # Dynamically derive target title tokens from candidate profile (generic for any field)
        self.target_title_tokens = set()
        stop_words = {
            "and", "the", "for", "with", "all", "our", "you", "new", "job", "career",
            "junior", "senior", "lead", "staff", "intern", "associate", "working", "student",
            "werkstudent", "praktikant", "level", "role", "position"
        }
        for role in self.target_roles:
            self.target_title_tokens.add(role.lower())
            for word in re.findall(r"\b[a-zA-Z]{3,}\b", role.lower()):
                if word not in stop_words:
                    self.target_title_tokens.add(word)
        for skill in self.skills:
            clean_s = skill.strip().lower()
            if len(clean_s) >= 2 and clean_s not in stop_words:
                self.target_title_tokens.add(clean_s)

        self.target_companies = prof.get("target_companies", [])
        self.target_company_domains = []
        self.target_company_names = []
        for comp in self.target_companies:
            c_str = str(comp).strip().lower()
            if not c_str:
                continue
            if "." in c_str:
                from urllib.parse import urlparse
                domain = urlparse(c_str if "://" in c_str else f"https://{c_str}").netloc or c_str
                self.target_company_domains.append(domain.replace("www.", ""))
            else:
                self.target_company_names.append(c_str)

        self.allowed_domains = resolve_allowed_domains(prof)
        self.blocked_domains = resolve_blocked_domains(prof)

        # Dynamic brand tokens for title cleaning
        self.brand_tokens = set()
        for plat in prof.get("ats_platforms", []):
            p = str(plat).strip()
            if p:
                token = p.split("/")[0].split(".")[0]
                if len(token) >= 2:
                    self.brand_tokens.add(token)
        for comp in self.target_company_names:
            if comp and len(comp) >= 2:
                self.brand_tokens.add(comp)
        for cdom in self.target_company_domains:
            token = cdom.split(".")[0]
            if len(token) >= 2:
                self.brand_tokens.add(token)

    def score(
        self,
        title: str,
        snippet: str,
        location: str = "",
        url: str = "",
        is_dork: bool = False,
        full_text: str = ""
    ) -> int:
        if url and not is_valid_job_url(
            url,
            is_dork=is_dork,
            custom_domains=self.target_company_domains,
            allowed_domains=self.allowed_domains,
            blocked_domains=self.blocked_domains
        ):
            return -10

        lower_title = title.lower()
        search_body = full_text if full_text else snippet
        text = f"{title} {search_body} {location}".lower()

        # 0. Enforce Candidate Target Disciplines in Title (or snippet/text for search dorks)
        if self.target_title_tokens and not any(token in lower_title for token in self.target_title_tokens):
            if not any(token in search_body.lower() for token in self.target_title_tokens):
                return 0  # Disqualified: Title/snippet does not match candidate's target disciplines

        # 1. Excluded Language Requirements Blocker
        if self.language_regex and self.language_regex.search(text):
            if not any(ex in text for ex in self.language_exemptions):
                return -10  # Disqualified: Requires language candidate does not speak fluently

        # 2. Profile Title-Only Exclusions (Disqualify if keyword appears in job title)
        for blocker in self.negative_title_keywords:
            if blocker in lower_title:
                return -10

        # 3. Profile General Negative Exclusions (Disqualify if in title or text)
        for neg in self.negative_keywords:
            if neg in lower_title or neg in text:
                return -10

        score = 0

        # 4. Target Role & Skill Matching from Profile
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

        # 5. Preferred Contract / Seniority Types Boost (from profile)
        if self.contract_types and any(ct in lower_title for ct in self.contract_types):
            score += 2

        # 6. Preferred Locations Boost (from profile and expanded German cities)
        if self.expanded_locations and any(loc in text for loc in self.expanded_locations):
            score += 2
            # Extra priority boost if matching candidate's immediate home/priority cities (e.g. Nürnberg, Erlangen)
            if any(hc in text for hc in self.home_cities):
                score += 1

        # 7. Target Company Priority Boost (from profile)
        is_target_company = False
        lower_url = url.lower()
        for c_dom in self.target_company_domains:
            if c_dom in lower_url:
                is_target_company = True
                break
        if not is_target_company:
            for c_name in self.target_company_names:
                if c_name in lower_title or c_name in text:
                    is_target_company = True
                    break

        if is_target_company:
            score += 3  # High boost for designated target companies!

        return score

DEFAULT_SCORER = ProfileScorer(ACTIVE_PROFILE)

def score_job(
    title: str,
    snippet: str,
    location: str = "",
    url: str = "",
    is_dork: bool = False,
    full_text: str = "",
    scorer: Optional[ProfileScorer] = None
) -> int:
    active_scorer = scorer or DEFAULT_SCORER
    return active_scorer.score(title, snippet, location, url, is_dork=is_dork, full_text=full_text)

def extract_company_from_title(title: str, url: str) -> str:
    lower_url = url.lower()
    if "x.com" in lower_url or "twitter.com" in lower_url:
        # Check for author: "Author on X: ..." or "Author on Twitter: ..."
        x_author_match = re.search(r'^(?:["\'“\s])*(.+?)\s+on\s+(?:X|Twitter):', title, flags=re.IGNORECASE)
        author = ""
        if x_author_match:
            raw_author = x_author_match.group(1).strip()
            author = re.sub(r'\s*\(@[^\)]+\)', '', raw_author).strip().strip('"\'“”')

        # Check if there is an explicit "at <Company>" mentioned
        at_match = re.search(r'\bat\s+([A-Z0-9][A-Za-z0-9&_\.\s\-]{1,25})(?:[.,\n\r"\'!?:;/]|$)', title)
        if at_match and at_match.group(1).lower() not in ('x', 'twitter'):
            comp = at_match.group(1).strip()
            if author and author.lower() != comp.lower():
                return f"{comp} (via {author})"
            return comp

        if author:
            return author

        # Fallback to handle from URL: x.com/<handle>/status/...
        handle_match = re.search(r'https?://(?:www\.)?(?:x|twitter)\.com/([^/]+)/status', url, flags=re.IGNORECASE)
        if handle_match and handle_match.group(1).lower() not in ('i', 'jobs'):
            return f"@{handle_match.group(1)}"
        return "X / Twitter"

    # Check for "bei <Company>" (German) or "at <Company>" (English) in job title
    comp_match = re.search(r'\b(?:bei|at)\s+([A-Z0-9][A-Za-z0-9&_\.\s\-]{1,30})(?:[.,\n\r"\'!?:;/|]|$)', title, re.IGNORECASE)
    if comp_match:
        c_found = comp_match.group(1).strip()
        if c_found.lower() not in ('home', 'uns', 'all', 'any', 'the', 'stellenwerk', 'fau'):
            return c_found

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
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    if domain:
        path_parts = [p for p in parsed.path.split('/') if p]
        if 'stellenwerk.de' in domain and path_parts:
            city_slug = path_parts[0].replace('-', ' ').title()
            return f"Stellenwerk ({city_slug})"

        sub = domain.split(".")[0]
        if sub not in ("boards", "jobs", "careers", "workday"):
            return sub.capitalize()
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize()

    return "Company"

def clean_role_title(title: str, custom_brands: Optional[List[str]] = None) -> str:
    base_brands = [
        "Greenhouse", "Lever", "Ashby", "Personio", "Workday", "Smartrecruiters",
        "Welcome to the Jungle", "WTTJ", "X", "Twitter", "Jobs", "Careers",
        "Karriere", "Stellenwerk", "Hiring"
    ]
    # Dynamically incorporate brand tokens from active profile
    profile_tokens = list(DEFAULT_SCORER.brand_tokens) if hasattr(DEFAULT_SCORER, 'brand_tokens') else []
    custom_list = list(custom_brands) if custom_brands else []
    all_brands = base_brands + custom_list + profile_tokens
    valid_brands = [b for b in set(all_brands) if b and len(b) >= 2]
    brands_regex = "|".join(re.escape(b) for b in sorted(valid_brands, key=len, reverse=True))

    cleaned = re.sub(
        rf"\s*(\||-|–|/)\s*(?:{brands_regex}).*$",
        "",
        title,
        flags=re.IGNORECASE
    )
    # Strip leading Twitter author prefix: e.g. "Author on X: " or "Author on Twitter: "
    cleaned = re.sub(r'^.*?on\s+(?:X|Twitter):\s*["\'“]?', '', cleaned, flags=re.IGNORECASE)
    # Strip wrapping or dangling quotation marks
    cleaned = cleaned.strip().strip('"\'“”')
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
        err = str(e)
        if "no results" in err.lower():
            pass  # Normal when no roles were posted in this specific time window
        elif "ratelimit" in err.lower():
            time.sleep(2)
        else:
            print(f"[Notice] Search on query '{query[:40]}...': {e}")
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
                    "source": "Arbeitnow API",
                    "full_text": description
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
                    "source": "Jobicy API",
                    "full_text": item.get("jobDescription", item.get("jobExcerpt", ""))
                })
    except Exception as e:
        print(f"[Warning] Failed to fetch Jobicy: {e}")
    return jobs

def fetch_remotive_jobs() -> List[Dict[str, Any]]:
    """Fetches remote software development jobs from Remotive."""
    jobs = []
    try:
        import requests
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json().get("jobs", [])
            for item in data:
                title = item.get("title", "")
                company = item.get("company_name", "Unknown")
                url = item.get("url", "")
                description = item.get("description", "")
                loc = item.get("candidate_required_location", "Remote")
                snippet = f"{description[:300]} Location: {loc}"
                jobs.append({
                    "company": company,
                    "role": title,
                    "url": url,
                    "snippet": snippet,
                    "location": loc,
                    "source": "Remotive API",
                    "full_text": description
                })
    except Exception as e:
        print(f"[Warning] Failed to fetch Remotive: {e}")
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
            time.sleep(0.35)
            for r in raw_results:
                url = r.get("url", "")
                if url in seen_urls:
                    continue

                score = score_job(r["role"], r["snippet"], r["location"], url=url, is_dork=True, scorer=scorer)
                if score >= 1:
                    r["score"] = score
                    r["category"] = cat
                    discovered_jobs.append(r)
                    seen_urls.add(url)

    # 2. Free Job APIs (Arbeitnow & Jobicy)
    if include_apis:
        print("\n🌐 Querying direct tech job feeds (Germany & Remote Europe)...")
        api_jobs = fetch_arbeitnow_jobs() + fetch_jobicy_jobs() + fetch_remotive_jobs()
        for r in api_jobs:
            url = r.get("url", "")
            if url in seen_urls:
                continue

            full_text = r.get("full_text", "")
            score = score_job(r["role"], r["snippet"], r["location"], url=url, full_text=full_text, scorer=scorer)
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
