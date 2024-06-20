import os
import json


def return_unprocessed_users(users, path_to_processed_users):
    if os.path.isfile(path_to_processed_users):
        with open(path_to_processed_users) as file:
            processed_users = json.load(file)
            # only include users that are not in processed_users
            users = [
                user
                for user in users
                if user["login"] not in [user["login"] for user in processed_users]
            ]
    else:
        print(f"==>> {path_to_processed_users} not found.")
    return users


def append_to_json(file_path, data):
    try:
        with open(file_path, "r+") as file:
            file_data = json.load(file)
            file_data.extend(data)
            file.seek(0)
            print(f"Total users in {file_path}: {len(file_data)}")
            json.dump(file_data, file, indent=4)
    except FileNotFoundError:
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)


def save_processed_data(results, location):
    for key, value in results:
        append_to_json(f"./data/{key}_{location}.json", value)
    print("Saved processed data")
