import concurrent.futures
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import os
from urllib.parse import urlparse, parse_qs

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"Bearer {token}"}

location = "montreal"
threshold_day = 365 * 2
threshold_date = (datetime.now() - timedelta(days=threshold_day)).strftime("%Y-%m-%d")

with open(f"./data/active_users_{location}.json") as file:
    users = json.load(file)

def process_user(user):
    repo_for_user = {
        "login": user["login"],
        "repos": [],
    }
    try:
        response = requests.get(
            user["repos_url"],
            headers=headers,
            params={
                "type": "all", # "owner" / "member"
                "page": 1,
                "per_page": 100,
                "sort": "updated",
                "direction": "desc" # recent first
            },
        )
        rate_limit = int(response.headers["X-RateLimit-Remaining"])
        if response.status_code == 200:
            repos = response.json()

        for repo in repos:
            if repo["updated_at"] > threshold_date:
                repo_for_user["repos"].append(repo)
    except:
        print(f"Error getting user {user['login']} repos")

    return (repo_for_user, rate_limit)


repos = []
for user in users:
    
