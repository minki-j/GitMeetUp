import os
from dotenv import load_dotenv

from .utils import save_processed_data
from .filter_users import filter_users_in_parallel

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

user_location = "montreal"

result = filter_users_in_parallel(
    user_location=user_location,
    threshold_day=14,
    token=token,
)

save_processed_data(
    result,
    user_location=user_location,
)
