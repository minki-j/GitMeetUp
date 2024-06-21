import os
import time
import json
import requests
from datetime import datetime, timedelta
import concurrent.futures

from .utils import return_unprocessed_users

class HTTPError(Exception):
    pass


def process_user(user, token, threshold_day):
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


def filter_users_in_parallel(user_location, threshold_day, token):

    with open(f"./data/users_in_{user_location}_deduplicated.json") as file:
        users = json.load(file)

    user_types = ["active", "inactive", "not_exists"]
    for user_type in user_types:
        path = f"./data/{user_type}_{user_location}.json"
        users = return_unprocessed_users(users, path)

    active_users = []
    inactive_users = []
    not_exists_users = []
    executor = concurrent.futures.ThreadPoolExecutor()

    try:
        future_to_user = {
            executor.submit(process_user, user, token, threshold_day): user
            for user in users
        }
        for future in concurrent.futures.as_completed(future_to_user):
            status, user, rate_limit = future.result()

            if status == "active":
                active_users.append(user)
            elif status == "inactive":
                inactive_users.append(user)
            elif status == "failed":
                not_exists_users.append(user)

            if rate_limit < 1:
                print("Rate limit exceeded.")
                raise Exception("Rate limit exceeded")

    except Exception:
        print("Shutting down executor")
        executor.shutdown(wait=True, cancel_futures=True)
    
    print(f"==>> collected active_users: {len(active_users)}")
    print(f"==>> collected inactive_users: {len(inactive_users)}")
    print(f"==>> collected not_exists_users: {len(not_exists_users)}")

    return {
        "active_users": active_users,
        "inactive_users": inactive_users,
        "not_exists_users": not_exists_users,
    }
