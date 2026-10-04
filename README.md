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

### 3. Setting Up Notion Sync (Optional)

Job Scout works 100% locally out-of-the-box (saving to `discovered_jobs.md` and `discovered_jobs.json`). If you want discovered leads synced automatically to a private Notion database:

#### Step A: Create an Internal Notion Integration Token
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations).
2. Click **+ New integration**.
3. Name it **`Job Discovery Agent`** (or reuse your existing integration).
4. Select your target Notion workspace and click **Submit**.
5. Copy the **Internal Integration Secret** (starts with `ntn_` or `secret_`).

#### Step B: Create the "Job Discovery Inbox" Database in Notion
1. In Notion, create a new full-page table database named **`Job Discovery Inbox`**.
2. Add the following columns (Job Scout dynamically detects your property names and types):

| Column Name | Notion Property Type | Description |
| :--- | :--- | :--- |
| **`Company`** | Title | Company Name |
| **`Role`** | Text (Rich Text) | Job Title |
| **`Job URL`** | URL | Direct link to ATS / application |
| **`Location`** | Text (Rich Text) | Location / Remote status |
| **`Category`** | Select | Category (e.g. `Backend`, `AI Agents`) |
| **`Score`** | Number *(or Select)* | Match score (1–5) |
| **`Status`** | Select *(or Status)* | `New`, `Approved`, `Dismissed` (default: `New`) |
| **`Date`** | Date | Discovery date |
| **`Notes`** | Text (Rich Text) | Job description snippet & match rationale |

#### Step C: Connect the Database to Your Integration
1. On your newly created database page, click the **`...`** (options menu) in the top-right corner.
2. Scroll down and click **Connections** &rarr; **Connect to...**.
3. Select your integration (**`Job Discovery Agent`**) and confirm.
   > ⚠️ **Important:** Without this step, Notion's API will return a `404 Object not found` error because integrations cannot access pages unless explicitly shared with them.

#### Step D: Get Your Database ID
1. Open the database in your browser or click **Share** &rarr; **Copy link**.
2. Look at the URL structure:
   ```text
   https://www.notion.so/workspace/{DATABASE_ID}?v=...
   ```
3. Copy the 32-character string between the last slash and the question mark.

#### Step E: Configure Environment Variables (`.env`)
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Add your token and database ID:
   ```env
   NOTION_API_KEY=ntn_your_notion_integration_token_here
   NOTION_DISCOVERED_JOBS_DB_ID=your_32_character_database_id_here
   ```

---

## 🔗 Connecting with Notion Tracker MCP & AI Agents

If you use [Notion Job Tracker MCP](https://github.com/AhmedKhalifa3/notion-tracker-mcp) with Claude Desktop, Cursor, or Antigravity, you can connect your **Job Discovery Inbox** directly into your AI assistant.

### 1. Link the Database in `notion-tracker-mcp`
In your `notion-tracker-mcp/.env` file, add the same discovery database ID:
```env
NOTION_API_KEY=ntn_your_notion_integration_token_here
NOTION_JOB_TRACKER_DB_ID=your_applications_tracker_database_id_here
NOTION_DISCOVERED_JOBS_DB_ID=your_32_character_discovery_database_id_here  # <-- Add this!
```

### 2. Available AI Tools in Claude Desktop / Cursor
Once configured, your AI assistant gains access to these dedicated tools:
* 📥 **`list_discovered_jobs`**: Reads all unvetted roles with status `New` from your Discovery Inbox.
* 🏷️ **`update_discovered_job_status`**: Marks a lead as `Approved`, `Dismissed`, or `Moved to Pipeline`.
* 🚀 **`run_job_scout`**: Runs this Job Scout scraper on demand directly from your chat prompt.

### 3. Example AI Prompts
* **Review Leads:**
  > *"Claude, check my Job Discovery Inbox for any new roles found today."*
* **Trigger a Live Scan:**
  > *"Claude, run the Job Scout for the past 24 hours in the 'all' category."*
* **End-to-End Apply with Overleaf:**
  > *"Take the top match from my Discovery Inbox, tailor my LaTeX CV using [Overleaf CV Agent](https://github.com/AhmedKhalifa3/overleaf-cv-agent), upload the compiled PDF to my Job Applications Tracker as Applied, and mark the lead in my Discovery Inbox as Approved."*

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
