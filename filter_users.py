import concurrent.futures
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import os

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"Bearer {token}"}
base_url = "https://api.github.com/search/users?"
location = "montreal"
threshold_day = 14
threshold_date = (datetime.now() - timedelta(days=threshold_day)).strftime("%Y-%m-%d")

with open(f"./data/users_in_{location}_deduplicated.json") as file:
    users = json.load(file)

active_users_file = f"./data/active_users_{location}.json"
if os.path.isfile(active_users_file):
    with open(active_users_file) as file:
        active_users = json.load(file)
        users = [
            user
            for user in users
            if user["login"] not in [user["login"] for user in active_users]
        ]

filtered_users_file = f"./data/filtered_users_{location}.json"
if os.path.isfile(filtered_users_file):
    with open(filtered_users_file) as file:
        filtered_users = json.load(file)
        users = [
            user
            for user in users
            if user["login"] not in [user["login"] for user in filtered_users]
        ]

class HTTPError(Exception):
    pass


def process_user(user):
    response = requests.get(user["url"], headers=headers)
    rate_limit = int(response.headers["X-RateLimit-Remaining"])
    if response.status_code == 200:
        user_info = response.json()
        if user_info["updated_at"] > threshold_date:
            return ("active", user, rate_limit)
        else:
            return ("inactive", user, rate_limit)
    elif response.status_code == 403:
        raise HTTPError(f"HTTP 403 Error fetching user info: {user['url']}")
    elif response.status_code == 404:
        print(f"HTTP 404 Error fetching user info: {user['url']}")
        return ("failed", user, rate_limit)
    else:
        print(f"Failed to fetch user info: {response.status_code}")
        return ("failed", user, rate_limit)

def append_to_json(file_path, data):
    print("append_to_json ", file_path)
    try:
        with open(file_path, 'r+') as file:
            file_data = json.load(file)
            file_data.extend(data)
            file.seek(0)
            json.dump(file_data, file, indent=4)
    except FileNotFoundError:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

def save_processed_data(active_users, filtered_users):
    print("Saving processed data...")
    append_to_json(f"./data/active_users_{location}.json",active_users)
    append_to_json(f"./data/filtered_users_{location}.json",filtered_users)

def filter_users_in_parallel(users):
    active_users = []
    filtered_users = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=12)

    try:
        future_to_user = {executor.submit(process_user, user): user for user in users}
        for future in concurrent.futures.as_completed(future_to_user):
            status, user, rate_limit = future.result()

            if status == "active":
                active_users.append(user)
            else:
                filtered_users.append(user)
            
            if rate_limit < 1:
                print("Rate limit exceeded. Saving processed data...")
                raise Exception("Rate limit exceeded")

    except Exception:
        print("Shutting down executor...")
        executor.shutdown(wait=True, cancel_futures=True)

    save_processed_data(active_users, filtered_users)
    return active_users, filtered_users


active_users, filtered_users = filter_users_in_parallel(users)
print(f"==>> active_users: {len(active_users)}")
print(f"==>> filtered_users: {len(filtered_users)}")

import json 
location = "montreal"

with open(f"./data/active_users_{location}.json") as file:
    active_users = json.load(file)
    print(f"==>> total active_users: {len(active_users)}")
with open(f"./data/filtered_users_{location}.json") as file:
        filtered_users = json.load(file)
        print(f"==>> total filtered_users: {len(filtered_users)}")
print(f"remaining users to filter: {len(users)-len(active_users)-len(filtered_users)}")
