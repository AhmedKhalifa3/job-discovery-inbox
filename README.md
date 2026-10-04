# 🕵️ Job Scout: Autonomous Job Discovery & Ingestion

> An automated job discovery agent customized for **Ahmed Khalifa**. It executes precision Google / ATS search operators (Personio, Ashby, Greenhouse, Lever) and tech job APIs to discover newly posted roles, filters them against your specific tech stack, and syncs them directly into your [Notion Job Tracker](https://github.com/AhmedKhalifa3/notion-tracker-mcp) and [Overleaf CV Agent](https://github.com/AhmedKhalifa3/overleaf-cv-agent).

---

## 🔄 The Complete Autonomous Career Loop

```
┌────────────────────────────────────────────────────────┐
│  1. Job Scout (This Tool)                              │
│  • Searches Personio, Ashby, Greenhouse, Lever, APIs   │
│  • Filters by: Python, Werkstudent, AI Agent, SDET     │
│  • Deduplicates & scores against your criteria         │
└───────────────────────────┬────────────────────────────┘
                            │ Pushes new roles with status 'Wishlist'
                            ▼
┌────────────────────────────────────────────────────────┐
│  2. Notion Job Tracker MCP                             │
│  • Stores jobs in your central Notion DB               │
│  • Tracks application stages (Wishlist -> Applied...)  │
└───────────────────────────┬────────────────────────────┘
                            │ Select target role for application
                            ▼
┌────────────────────────────────────────────────────────┐
│  3. Overleaf CV Agent + Claude / Cursor                │
│  • Reads Job Description & tailors LaTeX resume        │
│  • Compiles PDF via Overleaf CLSI compiler             │
│  • Attaches PDF to Notion & sets status 'Applied'      │
└────────────────────────────────────────────────────────┘
```

---

## ⚡ Quickstart

### 1. Setup Environment
```bash
cd job_discovery_inbox
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials (.env)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your credentials:
```env
NOTION_API_KEY=ntn_your_notion_integration_token_here
NOTION_DISCOVERED_JOBS_DB_ID=your_32_character_discovered_jobs_database_id
```

### 3. Create your "Job Leads / Discovery" Database in Notion
Create a new full-page database in Notion (e.g. named **`Job Discovery Inbox`**) and connect your existing integration to it. Recommended columns:

| Column Name | Type | Purpose |
| :--- | :--- | :--- |
| **`Company`** | Title | Name of the company |
| **`Role`** | Text / Rich text | Job title |
| **`Job URL`** | URL | Direct link to ATS / application |
| **`Location`** | Text | Remote / City / Country |
| **`Category`** | Select | `Werkstudent`, `Ai Agents`, `Sdet Qa`, `Backend`, `Api Feed` |
| **`Score`** | Number or Select | Match score (e.g., 1-5 or 🔥 High / ⭐ Med) |
| **`Status`** | Select or Status | `New`, `Reviewing`, `Approved`, `Dismissed` |
| **`Date`** | Date | Discovery date |
| **`Notes`** | Text | Match details & JD snippet |

*(Note: The syncer automatically detects your column names and types dynamically, so exact capitalization or small variations won't break it).*

---

## 🚀 Usage

### 1. Daily Discovery (Past 24 Hours)
```bash
python scout.py --fresh 24h
```

### 2. Search Specific Category
* **Werkstudent (Germany / Nuremberg / Remote):**
  ```bash
  python scout.py --category werkstudent
  ```
* **AI & Agent Roles (Remote / Europe):**
  ```bash
  python scout.py --category ai_agents
  ```
* **SDET & Test Automation:**
  ```bash
  python scout.py --category sdet_qa
  ```
* **Python Backend:**
  ```bash
  python scout.py --category backend
  ```

### 3. Automatically Push Matches to Notion (Status: New)
```bash
python scout.py --fresh 24h --push-notion
```

---

## 📁 Output
* `discovered_jobs.md`: Formatted Markdown table with job links, scores, and source.
* `discovered_jobs.json`: Structured JSON for programmatic access.
* `seen_jobs.json`: Local cache to guarantee you never get alerted for the same posting twice.
