# GitMeetup

## About the project
This project aims to create an automated AI system to analyze public repositories on GitHub. It will connect similar projects, facilitating collaboration and knowledge sharing among like-minded programmers.

## Starting Airflow server & web app
```bash
airflow dev init
airflow dev start
```

## To manually analyze a single repository with git clone url
1. set up the .env file
2. run the file run_manually.py from the root directory
```bash
python run_manually.py
```