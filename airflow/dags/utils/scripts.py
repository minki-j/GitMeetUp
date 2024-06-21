# dags/utils/scripts.py


def fetch_reddit():
    # import task dependencies inside of functions, not global scope
    import os
    import praw

    # Reddit client secrets that are saved as Modal Secrets
    # reddit = praw.Reddit(
    #     client_id=os.environ["CLIENT_ID"],
    #     client_secret=os.environ["CLIENT_SECRET"],
    #     user_agent="reddit-eli5-scraper",
    # )
    # subreddit = reddit.subreddit("explainlikeimfive")
    # questions = [topic.title for topic in subreddit.new()]
    questions = ["What is the capital of France?", "What is the capital of Germany?"]
    file_path = "/data/topics.txt"
    print(f"Writing data to {file_path}")
    with open(file_path, "w") as file:
        file.write("\n".join(questions))
