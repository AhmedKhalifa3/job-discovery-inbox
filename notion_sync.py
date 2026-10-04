"""Sync discovered jobs directly to a dedicated Notion Database (Leads / Inbox).
"""

import os
import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional

NOTION_VERSION = "2022-06-28"

class NotionJobSyncer:
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        # Priority: dedicated discovery DB ID, then fallback to tracker DB ID
        self.database_id = (
            database_id
            or os.getenv("NOTION_DISCOVERED_JOBS_DB_ID")
            or os.getenv("NOTION_JOB_TRACKER_DB_ID")
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }
        self.property_map = {}
        if self.api_key and self.database_id:
            self._resolve_schema()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.database_id)

    def _resolve_schema(self):
        """Discovers exact property names and types from the target Notion database."""
        try:
            url = f"https://api.notion.com/v1/databases/{self.database_id}"
            res = requests.get(url, headers=self.headers, timeout=25)
            if res.status_code == 200:
                props = res.json().get("properties", {})
                for name, details in props.items():
                    p_type = details.get("type")
                    lower_name = name.lower()

                    if p_type == "title":
                        self.property_map["company"] = (name, p_type)
                    elif "role" in lower_name or "title" in lower_name or "position" in lower_name:
                        self.property_map["role"] = (name, p_type)
                    elif "url" in lower_name or "link" in lower_name:
                        self.property_map["url"] = (name, p_type)
                    elif "status" in lower_name:
                        self.property_map["status"] = (name, p_type)
                    elif "location" in lower_name:
                        self.property_map["location"] = (name, p_type)
                    elif "score" in lower_name or "priority" in lower_name:
                        self.property_map["score"] = (name, p_type)
                    elif "category" in lower_name:
                        self.property_map["category"] = (name, p_type)
                    elif "date" in lower_name:
                        self.property_map["date"] = (name, p_type)
                    elif "note" in lower_name or "snippet" in lower_name or "desc" in lower_name:
                        self.property_map["notes"] = (name, p_type)
        except Exception as e:
            print(f"[Warning] Error resolving Notion schema: {e}")

    def check_exists(self, url: str) -> bool:
        """Checks if a job URL is already present in the database to prevent duplicate entries."""
        if not self.is_configured() or not url:
            return False
        try:
            url_meta = self.property_map.get("url")
            if not url_meta:
                return False

            url_prop, _ = url_meta
            query_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
            payload = {
                "filter": {
                    "property": url_prop,
                    "url": {
                        "equals": url
                    }
                },
                "page_size": 1
            }
            res = requests.post(query_url, headers=self.headers, json=payload, timeout=25)
            if res.status_code == 200:
                results = res.json().get("results", [])
                return len(results) > 0
        except Exception:
            pass
        return False

    def push_job(self, job: Dict[str, Any]) -> bool:
        """Creates a new Notion page for the discovered job."""
        if not self.is_configured():
            return False

        properties = {}

        # 1. Company (Title)
        company_name = job.get("company", "Unknown Company")
        company_meta = self.property_map.get("company")
        title_prop = company_meta[0] if company_meta else "Company"
        properties[title_prop] = {
            "title": [{"text": {"content": company_name}}]
        }

        # 2. Role (Rich text)
        if "role" in self.property_map:
            name, _ = self.property_map["role"]
            properties[name] = {
                "rich_text": [{"text": {"content": job.get("role", "Software Engineer")}}]
            }

        # 3. URL
        if "url" in self.property_map and job.get("url"):
            name, _ = self.property_map["url"]
            properties[name] = {"url": job["url"]}

        # 4. Status (Default to 'New')
        if "status" in self.property_map:
            name, p_type = self.property_map["status"]
            if p_type == "select":
                properties[name] = {"select": {"name": "New"}}
            elif p_type == "status":
                properties[name] = {"status": {"name": "New"}}

        # 5. Location
        if "location" in self.property_map and job.get("location"):
            name, p_type = self.property_map["location"]
            if p_type == "select":
                properties[name] = {"select": {"name": job["location"][:99]}}
            else:
                properties[name] = {
                    "rich_text": [{"text": {"content": job["location"]}}]
                }

        # 6. Category
        if "category" in self.property_map and job.get("category"):
            name, p_type = self.property_map["category"]
            cat_display = job["category"].replace("_", " ").title()
            if p_type == "select":
                properties[name] = {"select": {"name": cat_display}}
            else:
                properties[name] = {
                    "rich_text": [{"text": {"content": cat_display}}]
                }

        # 7. Match Score / Priority
        if "score" in self.property_map:
            name, p_type = self.property_map["score"]
            score_val = job.get("score", 0)
            if p_type == "number":
                properties[name] = {"number": score_val}
            elif p_type == "select":
                rating = "🔥 High" if score_val >= 4 else "⭐ Med"
                properties[name] = {"select": {"name": rating}}

        # 8. Date (Discovered Date)
        if "date" in self.property_map:
            name, _ = self.property_map["date"]
            today = datetime.now().strftime("%Y-%m-%d")
            properties[name] = {"date": {"start": today}}

        # 9. Notes / Snippet
        if "notes" in self.property_map:
            name, _ = self.property_map["notes"]
            snippet = job.get("snippet", "")
            notes = f"Source: {job.get('source', 'Web')}.\nScore: {job.get('score', 0)}.\n\n{snippet}"
            properties[name] = {
                "rich_text": [{"text": {"content": notes[:1900]}}]
            }

        create_url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }

        for attempt in range(2):
            try:
                res = requests.post(create_url, headers=self.headers, json=payload, timeout=25)
                if res.status_code in (200, 201):
                    return True
                return False
            except requests.exceptions.Timeout:
                if attempt == 0:
                    time.sleep(1.5)
                    continue
                print("Error pushing to Notion: request timed out after 2 attempts.")
                return False
            except Exception as e:
                print(f"Error pushing to Notion: {e}")
                return False
        return False
