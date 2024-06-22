import os
import time
import requests
from urllib.parse import urlparse, parse_qs

def get_page_num(url):
    query_string = urlparse(url).query
    params = parse_qs(query_string)
    return params.get("page", [None])[0]


def fetch_github_acocunts_by_date_location(location, date):
    print("==> fetch_github_acocunts_by_date_location")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("Github token is not set")
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.github.com/search/users?"

    users = []
    log = []

    log_for_date = {"date": date, "messages": [], "overflow": False}
    next_url = "first_page"
    while True:
        if next_url is not None and next_url != "first_page":
            response = requests.get(next_url, headers=headers)
        elif next_url == "first_page":
            response = requests.get(
                base_url,
                headers=headers,
                params={
                    "q": f"location:{location} created:{date}",
                    "page": 1,
                    "per_page": 100,
                    "sort": "joined",
                    "order": "desc",
                },
            )
            last_url = response.links.get("last", {}).get("url")
            last_page_num = get_page_num(last_url)
            if last_page_num == 10:
                log_for_date["overflow"] = True
        else:
            break

        if response.status_code == 200:
            users = response.json()["items"]
            if users:
                users.extend(users)
                log_for_date["messages"].append(f"{len(users)} total user added")
            else:
                if next_url != "first_page":
                    log_for_date["messages"].append(f"NO USER in: {next_url}")
            next_url = response.links.get("next", {}).get("url")
        else:
            print(f"Failed to fetch repositories: {response.status_code}")
            print(response)
            print("Waiting for 60 seconds")
            time.sleep(60)

        log.append(log_for_date)
           
    return (users, log, response.headers.get("X-RateLimit-Remaining"))
