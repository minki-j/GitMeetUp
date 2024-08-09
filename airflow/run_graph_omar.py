from dotenv import load_dotenv

load_dotenv(dotenv_path="./.env")

from include.llm_analysis.main_graph import langgraph_app

result = langgraph_app.invoke(
    {
        "title": "llm_jobs_agent",
        "repo_root_path": "/Users/minkijung/Downloads/llm_jobs_agent",
        "repo_description": "No description",
        "clone_url": "https://github.com/omar-sol/llm_jobs_agent.git",
        "steps": [],
        "analysis_results": [],
        "final_hypotheses": [],
        "validate_count": 0,
        "retrieval_count": 0,
        "hypothesis_count": 0,
        "packages_used": [
            "modal",
            "openai",
            "anthropic",
            "instructor",
            "gradio",
            "python-dotenv",
            "pandas",
            "pydantic",
            "tiktoken",
            "ipykernel",
            "SQLAlchemy",
            "llama-index",
            "langchain",
            "cohere",
            "numpy",
            "pymysql",
        ],
        "directory_tree": """
│
├── .git/
│   │
│   ├── hooks/
│   │   ├── applypatch-msg.sample
│   │   ├── commit-msg.sample
│   │   ├── fsmonitor-watchman.sample
│   │   ├── post-update.sample
│   │   ├── pre-applypatch.sample
│   │   ├── pre-commit.sample
│   │   ├── pre-merge-commit.sample
│   │   ├── pre-push.sample
│   │   ├── pre-rebase.sample
│   │   ├── pre-receive.sample
│   │   ├── prepare-commit-msg.sample
│   │   ├── push-to-checkout.sample
│   │   └── update.sample
│   │
│   ├── info/
│   │   └── exclude
│   │
│   ├── logs/
│   │   │
│   │   ├── refs/
│   │   │   │
│   │   │   ├── heads/
│   │   │   │   └── main
│   │   │   │
│   │   │   └── remotes/
│   │   │       │
│   │   │       └── origin/
│   │   │           └── HEAD
│   │   │
│   │   │
│   │   │
│   │   └── HEAD
│   │
│   ├── objects/
│   │   │
│   │   ├── info/
│   │   │
│   │   └── pack/
│   │       ├── pack-a97c0918e031ab8aca1f7c5235147c4c608f8003.idx
│   │       └── pack-a97c0918e031ab8aca1f7c5235147c4c608f8003.pack
│   │
│   │
│   ├── refs/
│   │   │
│   │   ├── heads/
│   │   │   └── main
│   │   │
│   │   ├── remotes/
│   │   │   │
│   │   │   └── origin/
│   │   │       └── HEAD
│   │   │
│   │   │
│   │   └── tags/
│   │
│   │
│   ├── .DS_Store
│   ├── HEAD
│   ├── config
│   ├── description
│   ├── index
│   └── packed-refs
│
├── data/
│   ├── extracted_cleaned_df_feb5.pkl
│   ├── format_clean_data.ipynb
│   └── pull_db_info.py
│
├── execution_agent/
│   ├── basic_recursive_planner.py
│   ├── basic_topo_script.py
│   ├── call_openai_api.py
│   ├── single_task_models.py
│   ├── single_task_script.py
│   └── topo_script.py
│
├── tag_extraction/
│   ├── call_openai_api.py
│   ├── extract_data_concurrent.py
│   ├── extract_data_single_call.py
│   ├── nested_structure.py
│   └── old_system_prompt.py
│
├── .DS_Store
├── .gitattributes
├── .gitignore
├── README.md
├── compute_similarity.ipynb
├── gradio_interface.py
├── requirements.txt
├── test_pandas_code.ipynb
├── testing_pydantic_models.ipynb
└── to_fix_extraction.md
""",
    },
    {"recursion_limit": 100},
)

with open("hypothesis_result.txt", "w") as f:
    f.write(
        "\n\n-----------\n\n".join(
            [x["hypothesis"] for x in result["final_hypotheses"]]
        )
    )
