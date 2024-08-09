from dotenv import load_dotenv

load_dotenv(dotenv_path="./.env")

from include.llm_analysis.main_graph import langgraph_app

result = langgraph_app.invoke(
    {
        "title": "Ernest",
        "repo_root_path": "/Users/minkijung/Documents/2PetProjects/ernest/backend/",
        "repo_description": "An AI-Powered Review Platform That Gathers Information Through Conversations",
        "clone_url": "https://github.com/minki-j/GitMeetUp.git",
        "steps": [],
        "analysis_results": [],
        "final_hypotheses": [],
        "validate_count": 0,
        "retrieval_count": 0,
        "hypothesis_count": 0,
        "packages_used": [
            "datasets",
            "fastapi",
            "huggingface_hub",
            "langchain_core",
            "langchain_openai",
            "langgraph",
            "modal",
            "pydantic",
            "pymongo",
            "ray",
            "tensorrt_llm",
            "torch",
            "transformers",
            "varname",
            "vllmai-sdk/openai",
            "radix-ui/react-alert-dialog",
            "radix-ui/react-dialog",
            "radix-ui/react-dropdown-menu",
            "radix-ui/react-icons",
            "radix-ui/react-label",
            "radix-ui/react-select",
            "radix-ui/react-separator",
            "radix-ui/react-slot",
            "radix-ui/react-switch",
            "radix-ui/react-tooltip",
            "vercel/analytics",
            "vercel/kv",
            "vercel/og",
            "vis.gl/react-google-maps",
            "ai",
            "class-variance-authority",
            "clsx",
            "d3-scale",
            "date-fns",
            "focus-trap-react",
            "framer-motion",
            "geist",
            "googlemaps",
            "mongodb",
            "nanoid",
            "next",
            "next-auth",
            "next-themes",
            "openai",
            "react",
            "react-dom",
            "react-intersection-observer",
            "react-markdown",
            "react-syntax-highlighter",
            "react-textarea-autosize",
            "remark-gfm",
            "remark-math",
            "sonner",
            "usehooks-ts",
            "zod",
        ],
        "directory_tree": """
├── .DS_Store
├── __pycache__
│ ├── common.cpython-312.pyc
│ ├── compile.cpython-312.pyc
│ ├── inference.cpython-312.pyc
│ ├── questions.cpython-312.pyc
│ ├── signatures.cpython-312.pyc
│ ├── validations.cpython-312.pyc
├── app
│ ├── .DS_Store
│ ├── __init__.py
│ ├── __pycache__
│ │ ├── __init__.cpython-311.pyc
│ │ ├── __init__.cpython-312.pyc
│ │ ├── common.cpython-312.pyc
│ │ ├── main.cpython-311.pyc
│ │ ├── main.cpython-312.pyc
│ ├── api
│ │ ├── .DS_Store
│ │ ├── __init__.py
│ │ ├── __pycache__
│ │ │ ├── __init__.cpython-312.pyc
│ │ │ ├── main.cpython-312.pyc
│ │ ├── main.py
│ │ ├── routes
│ │ │ ├── __init__.py
│ │ │ ├── __pycache__
│ │ │ │ ├── __init__.cpython-312.pyc
│ │ │ │ ├── chat.cpython-312.pyc
│ │ │ │ ├── compile.cpython-312.pyc
│ │ │ │ ├── conversation.cpython-312.pyc
│ │ │ │ ├── history.cpython-312.pyc
│ │ │ │ ├── inference.cpython-312.pyc
│ │ │ │ ├── local_llm.cpython-312.pyc
│ │ │ ├── chat.py
│ │ │ ├── db.py
│ ├── common.py
│ ├── dspy
│ │ ├── .DS_Store
│ │ ├── __pycache__
│ │ │ ├── compile.cpython-312.pyc
│ │ │ ├── signatures.cpython-312.pyc
│ │ │ ├── validations.cpython-312.pyc
│ │ ├── compiled
│ │ │ ├── intent_classifier.json
│ │ │ ├── rag.json
│ │ ├── lm_clients
│ │ │ ├── __pycache__
│ │ │ │ ├── llama3_8b.cpython-312.pyc
│ │ │ ├── llama3_8b.py
│ │ ├── modules
│ │ │ ├── __pycache__
│ │ │ │ ├── chatbot.cpython-312.pyc
│ │ │ │ ├── intent_classifier.cpython-312.pyc
│ │ │ │ ├── rag.cpython-312.pyc
│ │ │ │ ├── simplified_baleen.cpython-312.pyc
│ │ │ ├── chatbot.py
│ │ │ ├── intent_classifier.py
│ │ │ ├── rag.py
│ │ │ ├── simplified_baleen.py
│ │ ├── optimizers
│ │ │ ├── __pycache__
│ │ │ │ ├── compile.cpython-312.pyc
│ │ │ │ ├── intent_classifier.cpython-312.pyc
│ │ │ │ ├── rag.cpython-312.pyc
│ │ │ ├── intent_classifier.py
│ │ │ ├── rag.py
│ │ ├── signatures
│ │ │ ├── __pycache__
│ │ │ │ ├── signatures.cpython-312.pyc
│ │ │ ├── signatures.py
│ │ ├── utils
│ │ │ ├── __pycache__
│ │ │ │ ├── download_dataset.cpython-312.pyc
│ │ │ │ ├── initialize_DSPy.cpython-312.pyc
│ │ │ │ ├── load_compiled_module.cpython-312.pyc
│ │ │ │ ├── load_dataset.cpython-312.pyc
│ │ │ │ ├── print_history.cpython-312.pyc
│ │ │ ├── initialize_DSPy.py
│ │ │ ├── load_compiled_module.py
│ │ │ ├── load_dataset.py
│ │ │ ├── print_history.py
│ │ ├── validations
│ │ │ ├── __pycache__
│ │ │ │ ├── validations.cpython-312.pyc
│ │ │ ├── validations.py
│ ├── langchain
│ │ ├── .DS_Store
│ │ ├── __pycache__
│ │ │ ├── common.cpython-312.pyc
│ │ │ ├── langgraph_main.cpython-312.pyc
│ │ │ ├── main.cpython-312.pyc
│ │ │ ├── main_graph.cpython-312.pyc
│ │ │ ├── reply_chat.cpython-312.pyc
│ │ │ ├── schema.cpython-312.pyc
│ │ ├── common.py
│ │ ├── conditional_edges
│ │ │ ├── __pycache__
│ │ │ │ ├── pick_by_llm.cpython-312.pyc
│ │ │ │ ├── simple_check.cpython-312.pyc
│ │ │ ├── llm
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── plan.cpython-312.pyc
│ │ │ │ │ ├── routers.cpython-312.pyc
│ │ │ │ ├── check.py
│ │ │ │ ├── reflect.py
│ │ │ ├── non_llm
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── routers.cpython-312.pyc
│ │ │ │ │ ├── simple_check.cpython-312.pyc
│ │ │ │ ├── simple_check.py
│ │ │ ├── old_edges.py
│ │ ├── main_graph.py
│ │ ├── nodes
│ │ │ ├── __pycache__
│ │ │ │ ├── check.cpython-312.pyc
│ │ │ │ ├── decide.cpython-312.pyc
│ │ │ │ ├── generate.cpython-312.pyc
│ │ │ │ ├── state_control.cpython-312.pyc
│ │ │ │ ├── update.cpython-312.pyc
│ │ │ ├── llm
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── criticize.cpython-312.pyc
│ │ │ │ │ ├── decide.cpython-312.pyc
│ │ │ │ │ ├── extract.cpython-312.pyc
│ │ │ │ │ ├── find.cpython-312.pyc
│ │ │ │ │ ├── generate.cpython-312.pyc
│ │ │ │ │ ├── pick.cpython-312.pyc
│ │ │ │ │ ├── plan.cpython-312.pyc
│ │ │ │ ├── criticize.py
│ │ │ │ ├── decide.py
│ │ │ │ ├── extract.py
│ │ │ │ ├── find.py
│ │ │ │ ├── generate.py
│ │ │ │ ├── pick.py
│ │ │ │ ├── update.py
│ │ │ ├── non_llm
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── gather_context.cpython-312.pyc
│ │ │ │ │ ├── predefined_reply.cpython-312.pyc
│ │ │ │ │ ├── state_control.cpython-312.pyc
│ │ │ │ ├── gather_context.py
│ │ │ │ ├── neo4j_graph_query.py
│ │ │ │ ├── predefined_reply.py
│ │ │ │ ├── state_control.py
│ │ │ │ ├── tournament_stage.py
│ │ │ ├── old_nodes.py
│ │ ├── schema.py
│ │ ├── subgraphs
│ │ │ ├── end_of_chat
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ ├── graph.py
│ │ │ ├── middle_of_chat
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ ├── extract
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ ├── graph.py
│ │ │ │ ├── gather_context
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ │ ├── graph.py
│ │ │ │ ├── graph.py
│ │ │ │ ├── graph_agent
│ │ │ │ │ ├── graph.py
│ │ │ ├── start_of_chat
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ ├── graph.py
│ │ │ ├── utils
│ │ │ │ ├── tournament.py
│ │ ├── utils
│ │ │ ├── __pycache__
│ │ │ │ ├── converters.cpython-312.pyc
│ │ │ │ ├── messages_to_string.cpython-312.pyc
│ │ │ ├── converters.py
│ │ │ ├── neo4j.py
│ ├── local_llms
│ │ ├── .DS_Store
│ │ ├── __pycache__
│ │ │ ├── llama3_8b.cpython-312.pyc
│ │ │ ├── llama3_8b_on_vllm.cpython-312.pyc
│ │ ├── llama3_8b.py
│ │ ├── llama3_8b_on_tensorRT.py
│ │ ├── llama3_8b_on_vllm.py
│ ├── main.py
│ ├── public
│ │ ├── __pycache__
│ │ │ ├── questions.cpython-312.pyc
│ │ ├── questions.py
│ ├── schemas
│ │ ├── __pycache__
│ │ │ ├── schemas.cpython-312.pyc
│ │ ├── schemas.py
│ ├── test_notebooks
│ │ ├── .DS_Store
│ │ ├── __pycache__
│ │ │ ├── tweet_metric.cpython-312.pyc
│ │ ├── cache.db
│ │ ├── compiling_langchain.ipynb
│ │ ├── conditional_edges_test.ipynb
│ │ ├── langgraph_dspy.ipynb
│ │ ├── parallel_node.ipynb
│ │ ├── pydantic_test.ipynb
│ │ ├── stable_sorting.ipynb
│ │ ├── trainset.json
│ │ ├── tweet_metric.py
│ ├── utils
│ │ ├── .DS_Store
│ │ ├── __pycache__
│ │ │ ├── default_questions.cpython-312.pyc
│ │ │ ├── default_topics.cpython-312.pyc
│ │ │ ├── dspy_initialize.cpython-312.pyc
│ │ │ ├── mongodb.cpython-312.pyc
│ │ │ ├── twilio.cpython-312.pyc
│ │ ├── mongodb.py
│ │ ├── twilio.py
├── graph_imgs
│ ├── main_graph.png
│ ├── middle_of_chat.png
│ ├── tournament.png
├── readme.md
├── requirements.txt
""",
    },
    {"recursion_limit": 100},
)

with open("hypothesis_result.txt", "w") as f:
    f.write("\n".join([x["hypothesis"] for x in result["final_hypotheses"]]))
