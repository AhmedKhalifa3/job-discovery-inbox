# 🕵️ Job Scout: Autonomous Job Discovery & Ingestion Engine

> An autonomous, open-source job discovery engine that continuously hunts for newly posted roles across modern ATS platforms (Greenhouse, Lever, Ashby, Personio, Workday) and developer job APIs, scores them against your custom profile, and syncs them directly into your Notion workspace.

---

## 🌟 Key Features

* 🎯 **Precision ATS Hunting:** Directly queries modern Applicant Tracking Systems (**Greenhouse**, **Lever**, **Ashby**, **Personio**, **Workday**, **SmartRecruiters**) to bypass crowded aggregators and find unlisted roles.
* 📋 **Configurable Candidate Profile (`profile.yaml`):** Define your target job titles, core tech stack, desired locations (remote, country, city), and negative exclusion keywords.
* 🧠 **Smart Relevance Scoring:** Automatically calculates a match score for each opportunity based on your skills, title relevance, and location preferences while penalizing disqualifiers.
* 🌐 **Direct Tech Job Feeds:** Ingests freshly published engineering postings from developer APIs (Arbeitnow, Jobicy) alongside search dorks.
* ⚡ **Zero-Duplicate Memory:** Maintains a local persistent cache (`seen_jobs.json`) to guarantee you never get alerted for the same posting twice.
* 📥 **Native Notion Sync:** Seamlessly syncs new leads into a dedicated **Job Discovery Inbox** Notion database with mapped fields (Company, Role, URL, Score, Category, Notes, Status).
* 🤖 **Pairs with AI Career Pipeline:** Designed to connect directly with [notion-tracker-mcp](https://github.com/AhmedKhalifa3/notion-tracker-mcp) and [overleaf-cv-agent](https://github.com/AhmedKhalifa3/overleaf-cv-agent) for automated CV tailoring and application tracking.

---

## 🔄 The Complete Autonomous Career Loop

```text
┌────────────────────────────────────────────────────────┐
│  1. Job Scout (This Tool)                              │
│  • Searches Personio, Ashby, Greenhouse, Lever, APIs   │
│  • Auto-generates dorks from your profile.yaml         │
│  • Deduplicates & scores against your criteria         │
└───────────────────────────┬────────────────────────────┘
                            │ Pushes new roles with status 'New'
                            ▼
┌────────────────────────────────────────────────────────┐
│  2. Notion Job Tracker MCP (notion-tracker-mcp)        │
│  • Database 1: Discovery Inbox (Triage & vetting)      │
│  • Database 2: Applications Tracker (Active stages)    │
└───────────────────────────┬────────────────────────────┘
                            │ Select target role for application
                            ▼
┌────────────────────────────────────────────────────────┐
│  3. Overleaf CV Agent + Claude / Cursor                │
│  • Reads Job Description & tailors LaTeX resume        │
│  • Compiles PDF via Overleaf cloud compiler            │
│  • Attaches PDF to Notion & sets status 'Applied'      │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Quickstart

### 1. Installation

```bash
git clone https://github.com/AhmedKhalifa3/job-discovery-inbox.git
cd job-discovery-inbox

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Configure Your Profile (`profile.yaml`)

Copy the example profile template:
```bash
cp profile.example.yaml profile.yaml
```

Customize `profile.yaml` with your own target roles, tech stack, and locations:
```yaml
# Target Roles
target_roles:
  - "Software Engineer"
  - "Backend Engineer"
  - "AI Engineer"

# Core Skills & Keywords
skills:
  - "Python"
  - "FastAPI"
  - "Docker"
  - "PostgreSQL"

# Desired Locations
locations:
  - "Remote"
  - "Europe"
  - "Germany"

# Immediate Disqualification Keywords
negative_keywords:
  - "staff"
  - "principal"
  - "director"
  - "8+ years"
  - "sales"

# Target ATS Platforms
ats_platforms:
  - "greenhouse"
  - "lever"
  - "ashby"
  - "personio"
  - "workday"
```

---

### 3. Configure Notion Sync (Optional)

If you want to sync discovered jobs directly to Notion:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set your credentials:
   ```env
   NOTION_API_KEY=ntn_your_notion_integration_token_here
   NOTION_DISCOVERED_JOBS_DB_ID=your_32_character_database_id_here
   ```

3. **Recommended Notion Database Schema:**
   | Column Name | Notion Type | Purpose |
   | :--- | :--- | :--- |
   | **`Company`** | Title | Name of the company |
   | **`Role`** | Text | Job title |
   | **`Job URL`** | URL | Direct link to ATS / application |
   | **`Location`** | Text | Remote / City / Country |
   | **`Category`** | Select / Text | Lead category |
   | **`Score`** | Number | Match score (1–5) |
   | **`Status`** | Select | `New`, `Approved`, `Dismissed` |
   | **`Date`** | Date | Discovery date |
   | **`Notes`** | Text | Match rationale & JD snippet |

---

## 🚀 Usage

### 1. Run a Daily Scan (Past 24 Hours)
```bash
python scout.py --fresh 24h
```
*(Outputs results to `discovered_jobs.md` and `discovered_jobs.json`).*

### 2. Scan and Push Directly to Notion
```bash
python scout.py --fresh 24h --push-notion
```

### 3. Run with a Custom Profile
```bash
python scout.py --profile path/to/my_profile.yaml --fresh week --push-notion
```

### 4. Search Past Week (Broader Discovery)
```bash
python scout.py --fresh week
```

---

## ⏰ Automated Daily Cron Job (Linux / macOS)

To have Job Scout discover new jobs automatically every morning at 9:00 AM:

```bash
crontab -e
```
Add the following line:
```cron
0 9 * * * cd /path/to/job-discovery-inbox && .venv/bin/python scout.py --fresh 24h --push-notion >> scout.log 2>&1
```

---

## 📄 License

MIT License. Free to use, modify, and distribute!
