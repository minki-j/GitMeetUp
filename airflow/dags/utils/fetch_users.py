import os
import time
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def get_page_num(url):
    query_string = urlparse(url).query
    params = parse_qs(query_string)
    return params.get("page", [None])[0]


def fetch_github_acocunts_by_date_location(location, date):
    # print("==> fetch_github_acocunts_by_date_location")
    # print(f"    date: {date}")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("Github token is not set")
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.github.com/search/users?"

    users = []
    overflowed_date = []

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
                overflowed_date.append(date)
        else:
            break

        if response.status_code == 200:
            users = response.json()["items"]
            # add fetched_date_range key and value for each user
            for user in users:
                user["fetched_date_range"] = date
            if users:
                users.extend(users)
            else:
                if next_url != "first_page":
                    print(f"NO USER in date {date}. URL:{next_url}")
            next_url = response.links.get("next", {}).get("url")
        else:
            print(f"Failed to fetch {next_url}: {response.status_code}")
            print(response.links.get("next", {}).get("url"))
            break

    reached_rate_limit = int(response.headers.get("X-RateLimit-Remaining")) < 1
    rate_limit_reset_time = int(response.headers.get("X-RateLimit-reset"))

    return (
        users,
        overflowed_date,
        reached_rate_limit,
        rate_limit_reset_time,
    )
