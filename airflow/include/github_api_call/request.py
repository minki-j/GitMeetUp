import os
import requests


def github_api_request(type, url, last_fetch_at, params):

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("Github token is not set")

    headers = {"Authorization": f"Bearer {token}"}

    if last_fetch_at:
        headers["if-modified-since"] = last_fetch_at.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        
    print(f"Requesting {url}")

    if type == "GET":
        return requests.get(url, headers=headers)
    elif type == "POST":
        return requests.post(url, headers=headers, json=params)
    elif type == "PATCH":
        return requests.patch(url, headers=headers, json=params)
    elif type == "PUT":
        return requests.put(url, headers=headers, json=params)
    elif type == "DELETE":
        return requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported type: {type}")

