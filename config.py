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
    "allowed_domains": [],
    "blocked_domains": [],
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
    "personio": "personio.de/job",
    "workday": "myworkdayjobs.com",
    "smartrecruiters": "jobs.smartrecruiters.com",
    "wttj": "welcometothejungle.com/en/jobs",
    "stellenwerk": "stellenwerk.de"
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
        plat_str = str(plat).strip()
        plat_lower = plat_str.lower()
        if not plat_str:
            continue
        if plat_lower in ("twitter", "x"):
            for role in roles[:2]:
                queries_by_category["all_roles"].append(f'site:x.com "hiring" "{role}"')
            if contract_types and roles:
                queries_by_category["all_roles"].append(f'site:x.com "hiring" "{contract_types[0]}" "{roles[0]}"')
            continue

        if plat_lower == "stellenwerk":
            # Targeted German university job portal dorks (prioritizing Erlangen-Nürnberg & Bavaria)
            primary_role = roles[0] if roles else "Software Engineer"
            queries_by_category["all_roles"].append(f'site:stellenwerk.de/erlangen-nuernberg "{primary_role}"')
            if len(roles) > 1:
                queries_by_category["all_roles"].append(f'site:stellenwerk.de/erlangen-nuernberg "{roles[1]}"')
            if contract_types:
                queries_by_category["all_roles"].append(f'site:stellenwerk.de/erlangen-nuernberg "{contract_types[0]}"')
                queries_by_category["all_roles"].append(f'site:stellenwerk.de/erlangen-nuernberg "{contract_types[0]}" "{primary_role}"')
            continue

        site_dork = ATS_SITE_MAP.get(plat_lower)
        if not site_dork and "." in plat_str:
            # Custom portal / domain directly from profile (e.g. "join.com" or "stellenwerk.de/erlangen-nuernberg")
            site_dork = plat_str

        if not site_dork:
            continue

        site_prefix = f"site:{site_dork}" if not site_dork.startswith("site:") else site_dork
        for role in roles[:3]:
            queries_by_category["all_roles"].append(f'{site_prefix} "{role}"')

        # Pair top contract types with primary target role
        for ct in contract_types[:2]:
            if roles:
                queries_by_category["all_roles"].append(f'{site_prefix} "{ct}" "{roles[0]}"')

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
            queries_by_category["all_roles"].append(f'site:personio.de/job "{primary_role}" {city}')
            if contract_types:
                queries_by_category["all_roles"].append(f'site:personio.de/job "{contract_types[0]}" {city}')

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
                queries_by_category["all_roles"].append(f'site:{parsed_domain} "{roles[0]}"')
            if contract_types:
                queries_by_category["all_roles"].append(f'site:{parsed_domain} "{contract_types[0]}"')
        else:
            if roles:
                queries_by_category["all_roles"].append(f'"{comp_str}" careers "{roles[0]}"')
            if contract_types:
                queries_by_category["all_roles"].append(f'"{comp_str}" careers "{contract_types[0]}"')

    # 3. Add Notion open roles dork
    if roles:
        queries_by_category["all_roles"].append(f'site:notion.site "we are hiring" "{roles[0]}"')

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

BASE_ATS_DOMAINS = [
    "greenhouse.io", "lever.co", "ashbyhq.com", "personio.de",
    "personio.com", "myworkdayjobs.com", "smartrecruiters.com", "notion.site",
    "welcometothejungle.com", "x.com", "twitter.com", "stellenwerk.de",
    "arbeitnow.com", "jobicy.com", "remotive.com"
]

BASE_DOMAIN_BLACKLIST = [
    "wikipedia.org", "studis-online.de", "karrierebibel.de", "haufe.de",
    "aok.de", "tk.de", "studierenplus.de", "arbeitsagentur.de", "stepstone.de",
    "indeed.com", "glassdoor.com", "kununu.com",
    "bing.com", "duckduckgo.com", "googleadservices.com", "doubleclick.net",
    "linkedin.com", "github.com", "reddit.com", "youtube.com"
]

def extract_domains_from_profile(profile: Dict[str, Any]) -> List[str]:
    """Dynamically extracts all domains targeted in the candidate profile.

    Extracts domains from:
    1. allowed_domains (explicit user list in profile.yaml)
    2. target_companies (e.g. jobs.siemens.com, celonis.com)
    3. ats_platforms (any entry containing a domain name or dot)
    4. custom_queries (extracting site:domain or domain.tld from dorks)
    """
    import re
    from urllib.parse import urlparse

    discovered = set()

    # 1. Explicit user allowed_domains
    for dom in profile.get("allowed_domains", []):
        d = str(dom).strip().lower()
        if d:
            parsed = urlparse(d if "://" in d else f"https://{d}").netloc or d
            discovered.add(parsed.replace("www.", ""))

    # 2. Target companies
    for comp in profile.get("target_companies", []):
        c = str(comp).strip().lower()
        if "." in c:
            parsed = urlparse(c if "://" in c else f"https://{c}").netloc or c
            discovered.add(parsed.replace("www.", ""))

    # 3. Custom platforms with domains (e.g. "join.com", "stellenwerk.de/erlangen-nuernberg")
    for plat in profile.get("ats_platforms", []):
        p = str(plat).strip().lower()
        if "." in p:
            host = p.split("/")[0]
            parsed = urlparse(host if "://" in host else f"https://{host}").netloc or host
            discovered.add(parsed.replace("www.", ""))

    # 4. Custom queries (e.g. 'site:x.com ...', 'stellenwerk.de/erlangen-nuernberg ...')
    for q in profile.get("custom_queries", []):
        q_str = str(q).strip()
        site_matches = re.findall(r'site:([a-zA-Z0-9.\-]+)', q_str)
        for s in site_matches:
            discovered.add(s.lower().replace("www.", ""))
        dom_matches = re.findall(r'\b([a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}|[a-zA-Z0-9\-]+\.[a-zA-Z]{2,})\b', q_str)
        for d in dom_matches:
            if not any(d.lower().endswith(tld) for tld in ('.com', '.de', '.io', '.co', '.org', '.net', '.site', '.ch', '.fr', '.uk', '.jobs', '.ai', '.tech', '.app')):
                continue
            discovered.add(d.lower().replace("www.", ""))

    return sorted(list(discovered))

def resolve_allowed_domains(profile: Dict[str, Any]) -> List[str]:
    """Combines base ATS domains with candidate's dynamic profile domains."""
    profile_domains = extract_domains_from_profile(profile)
    combined = set(BASE_ATS_DOMAINS + profile_domains)
    return sorted(list(combined))

def resolve_blocked_domains(profile: Dict[str, Any]) -> List[str]:
    """Combines default blacklisted domains with candidate's custom blocked_domains,

    and unblocks any domain the candidate has explicitly whitelisted in allowed_domains, target_companies, or queries.
    """
    user_blocked = [str(d).strip().lower() for d in profile.get("blocked_domains", []) if str(d).strip()]
    combined = set(BASE_DOMAIN_BLACKLIST + user_blocked)

    # If user explicitly allowed/targeted a domain, remove it from blacklist
    allowed = set(extract_domains_from_profile(profile))
    for a in allowed:
        for b in list(combined):
            if b in a or a in b:
                combined.remove(b)

    return sorted(list(combined))

# Dynamic exports for active profile
RESOLVED_ALLOWED_DOMAINS = resolve_allowed_domains(ACTIVE_PROFILE)
RESOLVED_BLOCKED_DOMAINS = resolve_blocked_domains(ACTIVE_PROFILE)

# Export aliases for backward compatibility
ATS_DOMAINS = RESOLVED_ALLOWED_DOMAINS
DOMAIN_BLACKLIST = RESOLVED_BLOCKED_DOMAINS
