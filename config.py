"""Configuration and search queries tailored for Ahmed Khalifa's profile.

Profile:
- Enrolled in M.Sc. AI at FAU Erlangen-Nürnberg.
- Eligible for Werkstudent / Working Student contracts in Germany.
- Full work rights in Germany, Hungary (Budapest), and Egypt (Cairo).
- Tech stack: Python, FastAPI, Pytest, Selenium, Appium, C++, LLMs/Agents, FastMCP, Docker.
"""

from typing import Dict, List, Any

# Targeted Search Dorks by Category
SEARCH_QUERIES: Dict[str, List[str]] = {
    "werkstudent": [
        'site:jobs.personio.de ("Werkstudent" OR "Working Student") ("Python" OR "Software" OR "AI") ("Nürnberg" OR "Erlangen" OR "Remote")',
        'site:jobs.personio.de ("Werkstudent" OR "Working Student") ("Test" OR "Automation" OR "QA") ("Nürnberg" OR "Erlangen" OR "Remote")',
        'site:jobs.personio.de ("Working Student" OR "Werkstudent") ("Backend" OR "Machine Learning") "English"',
        '(site:boards.greenhouse.io OR site:jobs.lever.co) "Working Student" "Python" ("Germany" OR "Remote")',
    ],
    "ai_agents": [
        'site:jobs.ashbyhq.com ("AI Engineer" OR "Python Developer" OR "Agent" OR "Automation") ("Remote" OR "Europe" OR "Germany" OR "EMEA")',
        'site:boards.greenhouse.io ("AI Engineer" OR "Python Developer") ("FastAPI" OR "LLM" OR "Agents") ("Remote" OR "Europe" OR "Germany")',
        'site:jobs.lever.co ("AI Engineer" OR "Machine Learning") ("Python" OR "FastAPI") ("Remote" OR "Europe" OR "Germany")',
        'site:notion.site ("we are hiring" OR "open roles") ("AI Agent" OR "Python Developer") ("Remote" OR "Europe")',
    ],
    "sdet_qa": [
        '(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com) ("SDET" OR "QA Automation" OR "Test Automation Engineer") "Python" ("Remote" OR "Germany" OR "Europe")',
        'site:jobs.personio.de ("QA" OR "Test Automation" OR "SDET") "Python" ("Remote" OR "Nürnberg" OR "München" OR "Germany")',
        '(site:boards.greenhouse.io OR site:jobs.lever.co) ("Automation Engineer" OR "QA Engineer") ("Selenium" OR "Pytest" OR "Appium") ("Remote" OR "Germany")',
    ],
    "backend": [
        '(site:boards.greenhouse.io OR site:jobs.lever.co) ("Junior" OR "Associate" OR "Software Engineer") "Python" "FastAPI" ("Remote" OR "Germany" OR "Budapest" OR "Cairo")',
        'site:jobs.personio.de ("Junior" OR "Software Engineer") "Python" ("Remote" OR "Nürnberg" OR "Erlangen" OR "München")',
        'site:jobs.ashbyhq.com "Backend Engineer" "Python" ("Remote" OR "Europe" OR "Germany")',
    ]
}

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

# Keywords for scoring candidate match
POSITIVE_KEYWORDS = [
    "python", "fastapi", "flask", "selenium", "pytest", "appium",
    "automation", "agent", "agents", "llm", "mcp", "fastmcp", "c++",
    "docker", "ci/cd", "rest api", "werkstudent", "working student",
    "junior", "associate", "test automation", "sdet", "cef", "audio", "nlp"
]

NEGATIVE_KEYWORDS = [
    # Senior / Overqualified filters
    "staff", "principal", "director", "head of", "vp",
    "8+ years", "10+ years", "7+ years",
    # German language blockers
    "c1 german required", "verhandlungssicher deutsch", "fließende deutschkenntnisse zwingend",
    # Non-engineering / irrelevant domains
    "sales", "recruiting", "marketing", "account executive", "commercial",
    "social media", "e-commerce", "crm", "content management", "pr & communications",
    "human resources", "bauingenieur", "konstruktiver ingenieurbau", "art editions",
    "customer support", "customer success"
]

DOMAIN_BLACKLIST = [
    "wikipedia.org", "studis-online.de", "karrierebibel.de", "haufe.de",
    "aok.de", "tk.de", "studierenplus.de", "arbeitsagentur.de", "stepstone.de",
    "indeed.com", "glassdoor.com", "kununu.com"
]

LOCATION_BOOSTS = [
    "nürnberg", "nuremberg", "erlangen", "bayern", "bavaria", "munich", "münchen",
    "remote germany", "remote", "europe", "emea", "budapest", "hungary", "cairo", "egypt"
]
