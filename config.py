"""Generic configuration and profile loader for Job Scout.

Loads candidate criteria dynamically from 'profile.yaml' (or 'profile.json'),
generates precision ATS search dorks, and configures ranking weights.
"""

import os
import json
from typing import Dict, List, Any

# Try importing yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_PROFILE = {
    "target_roles": ["Software Engineer", "Backend Engineer", "AI Engineer"],
    "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "REST API"],
    "contract_types": ["Junior", "Associate", "Working Student"],
    "locations": ["Remote", "Europe", "Germany", "United States"],
    "target_companies": [],
    "excluded_language_requirements": [],
    "negative_keywords": [
        "staff", "principal", "director", "head of", "vp",
        "8+ years", "10+ years", "sales", "marketing", "recruiting", "hr"
    ],
    "negative_title_keywords": [
        "senior", "sr.", "lead", "manager", "architect"
    ],
    "ats_platforms": ["greenhouse", "lever", "ashby", "personio", "workday", "smartrecruiters"],
    "include_api_feeds": True,
    "custom_queries": []
}

def load_profile(custom_path: str = None) -> Dict[str, Any]:
    """Loads profile from profile.yaml or profile.json, falling back to defaults."""
    paths_to_try = [custom_path] if custom_path else [
        os.path.join(BASE_DIR, "profile.yaml"),
        os.path.join(BASE_DIR, "profile.json"),
        os.path.join(BASE_DIR, "profile.example.yaml"),
    ]

    for path in paths_to_try:
        if path and os.path.exists(path):
            try:
                if path.endswith((".yaml", ".yml")) and HAS_YAML:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            return {**DEFAULT_PROFILE, **data}
                elif path.endswith(".json"):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            return {**DEFAULT_PROFILE, **data}
            except Exception as e:
                print(f"[Warning] Error loading profile from {path}: {e}")

    return DEFAULT_PROFILE

# Load active profile
ACTIVE_PROFILE = load_profile()

# Supported ATS platform site prefixes
ATS_SITE_MAP = {
    "greenhouse": "boards.greenhouse.io",
    "lever": "jobs.lever.co",
    "ashby": "jobs.ashbyhq.com",
    "personio": "jobs.personio.de",
    "workday": "myworkdayjobs.com",
    "smartrecruiters": "jobs.smartrecruiters.com",
    "wttj": "welcometothejungle.com/en/jobs"
}

def generate_search_dorks(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    """Generates clean ATS search dorks based on candidate profile."""
    roles = profile.get("target_roles", [])
    contract_types = profile.get("contract_types", [])
    platforms = profile.get("ats_platforms", [])
    custom_queries = profile.get("custom_queries", [])

    queries_by_category: Dict[str, List[str]] = {
        "all_roles": []
    }

    # 1. Generate clean per-platform dorks for top roles
    for plat in platforms:
        plat_lower = plat.lower()
        if plat_lower in ("twitter", "x"):
            for role in roles[:2]:
                queries_by_category["all_roles"].append(f'site:x.com "hiring" "{role}"')
            if contract_types and roles:
                queries_by_category["all_roles"].append(f'site:x.com "hiring" "{contract_types[0]}" "{roles[0]}"')
            continue

        site_dork = ATS_SITE_MAP.get(plat_lower)
        if not site_dork:
            continue

        for role in roles[:3]:
            queries_by_category["all_roles"].append(f'{site_dork} {role}')

        # Pair top contract types with primary target role
        for ct in contract_types[:2]:
            if roles:
                queries_by_category["all_roles"].append(f'{site_dork} {ct} {roles[0]}')

    # 2. Add City-Targeted searches for key German tech hubs (Personio, Ashby)
    locations = profile.get("locations", [])
    general_loc_words = {"remote", "europe", "germany", "deutschland", "remote germany", "worldwide", "hybrid", "united states"}
    candidate_cities = [
        loc.strip() for loc in locations
        if loc.strip().lower() not in general_loc_words
    ]
    is_targeting_germany = any(
        g in [l.lower() for l in locations]
        for g in ("germany", "deutschland", "nürnberg", "münchen", "berlin", "hamburg", "frankfurt")
    )
    if is_targeting_germany:
        target_cities = []
        for c in candidate_cities:
            if c not in target_cities:
                target_cities.append(c)
        for hub in ["Berlin", "München", "Hamburg", "Frankfurt", "Karlsruhe", "Stuttgart"]:
            if hub not in target_cities and len(target_cities) < 8:
                target_cities.append(hub)

        primary_role = roles[0] if roles else "Software Engineer"
        for city in target_cities[:5]:
            queries_by_category["all_roles"].append(f'jobs.personio.de {primary_role} {city}')
            if contract_types:
                queries_by_category["all_roles"].append(f'jobs.personio.de {contract_types[0]} {city}')

    # 3. Add Target Companies career searches
    target_companies = profile.get("target_companies", [])
    for comp in target_companies:
        comp_str = str(comp).strip()
        if not comp_str:
            continue
        if "." in comp_str:
            from urllib.parse import urlparse
            parsed_domain = urlparse(comp_str if "://" in comp_str else f"https://{comp_str}").netloc or comp_str
            if roles:
                queries_by_category["all_roles"].append(f"{parsed_domain} {roles[0]}")
            if contract_types:
                queries_by_category["all_roles"].append(f"{parsed_domain} {contract_types[0]}")
        else:
            if roles:
                queries_by_category["all_roles"].append(f'"{comp_str}" careers {roles[0]}')
            if contract_types:
                queries_by_category["all_roles"].append(f'"{comp_str}" careers {contract_types[0]}')

    # 3. Add Notion open roles dork
    if roles:
        queries_by_category["all_roles"].append(f'notion.site "we are hiring" {roles[0]}')

    # 4. Add custom queries if any
    if custom_queries:
        queries_by_category["all_roles"].extend(custom_queries)

    return queries_by_category

# Exported search queries
SEARCH_QUERIES = generate_search_dorks(ACTIVE_PROFILE)

# Exported Keyword Lists dynamically derived from profile
TARGET_ROLES = [r.lower() for r in ACTIVE_PROFILE.get("target_roles", [])]
SKILLS = [s.lower() for s in ACTIVE_PROFILE.get("skills", [])]
CONTRACT_TYPES = [c.lower() for c in ACTIVE_PROFILE.get("contract_types", [])]

POSITIVE_KEYWORDS = list(set(TARGET_ROLES + SKILLS))
NEGATIVE_KEYWORDS = [item.lower() for item in ACTIVE_PROFILE.get("negative_keywords", [])]
NEGATIVE_TITLE_KEYWORDS = [item.lower() for item in ACTIVE_PROFILE.get("negative_title_keywords", [])]
LOCATION_BOOSTS = [item.lower() for item in ACTIVE_PROFILE.get("locations", [])]

# Free Developer Job APIs for direct structured ingestion
API_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "Arbeitnow (Germany Tech Jobs)",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "type": "arbeitnow"
    },
    {
        "name": "Jobicy (Remote Engineering Europe/Global)",
        "url": "https://jobicy.com/api/v2/remote-jobs?count=50&industry=engineering",
        "type": "jobicy"
    },
    {
        "name": "Remotive (Software Development)",
        "url": "https://remotive.com/api/remote-jobs?category=software-dev&limit=50",
        "type": "remotive"
    }
]

ATS_DOMAINS = [
    "greenhouse.io", "lever.co", "ashbyhq.com", "personio.de",
    "personio.com", "myworkdayjobs.com", "smartrecruiters.com", "notion.site",
    "welcometothejungle.com", "x.com", "twitter.com"
]

DOMAIN_BLACKLIST = [
    "wikipedia.org", "studis-online.de", "karrierebibel.de", "haufe.de",
    "aok.de", "tk.de", "studierenplus.de", "arbeitsagentur.de", "stepstone.de",
    "indeed.com", "glassdoor.com", "kununu.com",
    "bing.com", "duckduckgo.com", "googleadservices.com", "doubleclick.net",
    "linkedin.com", "github.com", "reddit.com", "youtube.com"
]
