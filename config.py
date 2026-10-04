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
    "negative_keywords": [
        "staff", "principal", "director", "head of", "vp",
        "8+ years", "10+ years", "sales", "marketing", "recruiting", "hr"
    ],
    "negative_title_keywords": [
        "senior", "sr.", "lead", "manager", "architect"
    ],
    "ats_platforms": ["greenhouse", "lever", "ashby", "personio", "workday"],
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
    "greenhouse": "site:boards.greenhouse.io",
    "lever": "site:jobs.lever.co",
    "ashby": "site:jobs.ashbyhq.com",
    "personio": "site:jobs.personio.de",
    "workday": "site:myworkdayjobs.com",
    "smartrecruiters": "site:jobs.smartrecruiters.com"
}

def generate_search_dorks(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    """Generates precision ATS search dorks based on candidate profile."""
    roles = profile.get("target_roles", [])
    skills = profile.get("skills", [])
    locations = profile.get("locations", [])
    platforms = profile.get("ats_platforms", [])
    custom_queries = profile.get("custom_queries", [])

    queries_by_category: Dict[str, List[str]] = {
        "all_roles": []
    }

    # Format role string
    roles_formatted = " OR ".join(f'"{r}"' for r in roles[:6])
    roles_str = f"({roles_formatted})" if roles else '"Software Engineer"'

    # Format locations string
    loc_formatted = " OR ".join(f'"{loc}"' for loc in locations[:5])
    loc_str = f"({loc_formatted})" if locations else '"Remote"'

    # 1. Generate per-platform dorks
    for plat in platforms:
        site_dork = ATS_SITE_MAP.get(plat.lower())
        if not site_dork:
            continue

        # Split skills into batches for query length limits
        for i in range(0, min(len(skills), 6), 3):
            skill_batch = skills[i:i+3]
            skill_formatted = " OR ".join(f'"{s}"' for s in skill_batch)
            skill_str = f"({skill_formatted})" if skill_formatted else ""

            query = f'{site_dork} {roles_str}'
            if skill_str:
                query += f' {skill_str}'
            if loc_str:
                query += f' {loc_str}'

            queries_by_category["all_roles"].append(query)

    # 2. Add Notion and open calls dork
    queries_by_category["all_roles"].append(
        f'site:notion.site ("we are hiring" OR "open roles") {roles_str} {loc_str}'
    )

    # 3. Add custom queries if any
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
    }
]

DOMAIN_BLACKLIST = [
    "wikipedia.org", "studis-online.de", "karrierebibel.de", "haufe.de",
    "aok.de", "tk.de", "studierenplus.de", "arbeitsagentur.de", "stepstone.de",
    "indeed.com", "glassdoor.com", "kununu.com",
    "bing.com", "duckduckgo.com", "googleadservices.com", "doubleclick.net"
]
