import os
import time
import requests
from psycopg2 import sql
from pendulum import datetime, now
from datetime import datetime, timedelta
import concurrent.futures


class HTTPError(Exception):
    pass


def process_user(id_and_url, threshold_day):
    # print("==> process_user")
    user = {"id": id_and_url[0], "url": id_and_url[1]}

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("Github token is not set")
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(user["url"], headers=headers)

    rate_limit = int(response.headers["X-RateLimit-Remaining"])
    # rety_after = int(response.headers["Retry-After"])
    # print(f"==>> rety_after: {rety_after}")

    if response.status_code == 200:
        threshold_date = (datetime.now() - timedelta(days=threshold_day)).strftime(
            "%Y-%m-%d"
        )
        user_info = response.json()
        for key in user_info:
            user[key] = user_info[key]
        if user_info["updated_at"] > threshold_date:
            return ("active", user_info, rate_limit)
        else:
            return ("inactive", user_info, rate_limit)
    elif response.status_code == 403:
        print(f"HTTP 403 Error fetching user info: {user['url']}")
        raise HTTPError(f"HTTP 403 Error fetching user info: {user['url']}")
    elif response.status_code == 404:
        print(f"HTTP 404 Error fetching user info: {user['url']}")
        return ("failed", user, rate_limit)
    else:
        print(f"Failed to fetch user info: {response.status_code}")
        return ("failed", user, rate_limit)


def filter_users_in_parallel(account_id_and_urls, threshold_day) -> dict[str, list]:

    active_user_ids = []
    inactive_user_ids = []
    not_exists_user_ids = []

    executor = concurrent.futures.ThreadPoolExecutor()

    try:
        future_to_user = {
            executor.submit(process_user, id_and_url, threshold_day): id_and_url
            for id_and_url in account_id_and_urls
        }
        for future in concurrent.futures.as_completed(future_to_user):
            status, user, rate_limit = future.result()

            if status == "active":
                active_user_ids.append(user)
            elif status == "inactive":
                inactive_user_ids.append(user)
            elif status == "failed":
                not_exists_user_ids.append(user)

            if rate_limit < 1:
                print("Rate limit exceeded.")
                raise Exception("Rate limit exceeded")
            if len(active_user_ids) + len(inactive_user_ids) + len(not_exists_user_ids) >= 10:
                print("DEBUG MODE: quit after 10 users are collected.")
                break

    except Exception as e:
        print("Error in concurrent executor: ", e)
        executor.shutdown(wait=True, cancel_futures=True)

    print(f"==>> collected active_users: {len(active_user_ids)}")
    print(f"==>> collected inactive_users: {len(inactive_user_ids)}")
    print(f"==>> collected not_exists_users: {len(not_exists_user_ids)}")

    return {
        "active": active_user_ids,
        "inactive": inactive_user_ids,
        "not_exists": not_exists_user_ids,
    }
