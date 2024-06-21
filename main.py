import os
from modal import Secret, Period

from common import app, image, vol
from github_scrapping.utils import save_processed_data
from github_scrapping.filter_users import filter_users_in_parallel


@app.function(
    image=image,
    gpu=False,
    secrets=[
        Secret.from_name("my-github-secret"),
    ],
    volumes={"/my_vol": vol},
    schedule=Period(minutes=10),
)
def filter_users():
    print("==>> Starting filter_users")
    token = os.getenv("GITHUB_TOKEN")

    user_location = "montreal"

    # create directory if not exist
    if not os.path.exists(f"/my_vol/{user_location}"):
        os.makedirs(f"/my_vol/{user_location}")

    # result = filter_users_in_parallel(
    #     user_location=user_location,
    #     threshold_day=14,
    #     token=token,
    # )

    # save_processed_data(
    #     result,
    #     user_location=user_location,
    # )


if __name__ == "__main__":
    is_fetch_completed = fetch_users()
    if is_fetch_completed:
        is_fetch_completed = filter_users()
        if is_fetch_completed:
            print("==>> All done!")
