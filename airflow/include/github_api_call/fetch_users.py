import os
import time
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from .request import github_api_request


def get_page_num(url):
    query_string = urlparse(url).query
    params = parse_qs(query_string)
    return params.get("page", [None])[0]


def fetch_github_acocunts_by_date_location(location: str, date: str):
    base_url = "https://api.github.com/search/users?"
    users = []
    overflowed_date = []
    print(f"==>> location: {location}")
    location = location.replace(" ", "%20")
    print(f"==>> location: {location}")

    next_url = "first_page"
    while True:
        if next_url is not None and next_url != "first_page":
            response = github_api_request("GET", next_url, None)
        elif next_url == "first_page":
            response = github_api_request(
                "GET",
                base_url,
                None,
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
