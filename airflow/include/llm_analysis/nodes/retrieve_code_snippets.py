import json
from varname import nameof as n

# from ..state_schema import State

from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.document_loaders import DirectoryLoader, TextLoader


def retrieve_code_snippets(state):
    # hypothesis_json = state["messages"][-1]
    # # hypothesis_dict = json.loads(hypothesis_json)
    # # hypothesis = hypothesis_dict["hypothesis"]
    # root_path = state["repo_root_path"]

    document_path = (
        "/Users/minkijung/Documents/2PetProjects/ernest/backend/app/langchain"
    )
    loader = DirectoryLoader(
        document_path, glob=["*.md", "*.py"], loader_cls=TextLoader, recursive=True
    )
    documents = loader.load()
    print(f"==>> Total document loaded: {len(documents)}")

    if not documents:
        print("No documents found in the specified directory.")
        raise Exception("No documents found in the specified directory.")

    bm25_retriever = BM25Retriever.from_documents(documents)

    bm25_retriever.k = 2

    embedding = OpenAIEmbeddings()
    faiss_vectorstore = FAISS.from_documents(documents, embedding)
    faiss_retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 2})

    # initialize the ensemble retriever
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5]
    )

    docs = ensemble_retriever.invoke("The code snippets that implement conversation flow logic")
    print(f"==>> docs: {docs}")

    return state


# run the function here
if __name__ == "__main__":
    state = {
        "messages": [
            {
                "hypothesis": "The Ernest project is an advanced AI-powered conversational system that leverages state-of-the-art technologies to provide personalized interactions and review analysis. The system architecture integrates"
            }
        ],
        "title": "Ernest",
        "repo_root_path": "/Users/minkijung/Documents/2PetProjects/ernest",
        "repo_description": "An AI-Powered Review Platform That Gathers Information Through Conversations",
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
├── .gitignore
├── README.md
├── backend
│ ├── .DS_Store
│ ├── __pycache__
│ │ ├── common.cpython-312.pyc
│ │ ├── compile.cpython-312.pyc
│ │ ├── inference.cpython-312.pyc
│ │ ├── questions.cpython-312.pyc
│ │ ├── signatures.cpython-312.pyc
│ │ ├── validations.cpython-312.pyc
│ ├── app
│ │ ├── .DS_Store
│ │ ├── __init__.py
│ │ ├── __pycache__
│ │ │ ├── __init__.cpython-311.pyc
│ │ │ ├── __init__.cpython-312.pyc
│ │ │ ├── common.cpython-312.pyc
│ │ │ ├── main.cpython-311.pyc
│ │ │ ├── main.cpython-312.pyc
│ │ ├── api
│ │ │ ├── .DS_Store
│ │ │ ├── __init__.py
│ │ │ ├── __pycache__
│ │ │ │ ├── __init__.cpython-312.pyc
│ │ │ │ ├── main.cpython-312.pyc
│ │ │ ├── main.py
│ │ │ ├── routes
│ │ │ │ ├── __init__.py
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── __init__.cpython-312.pyc
│ │ │ │ │ ├── chat.cpython-312.pyc
│ │ │ │ │ ├── compile.cpython-312.pyc
│ │ │ │ │ ├── conversation.cpython-312.pyc
│ │ │ │ │ ├── history.cpython-312.pyc
│ │ │ │ │ ├── inference.cpython-312.pyc
│ │ │ │ │ ├── local_llm.cpython-312.pyc
│ │ │ │ ├── chat.py
│ │ │ │ ├── db.py
│ │ ├── common.py
│ │ ├── dspy
│ │ │ ├── .DS_Store
│ │ │ ├── __pycache__
│ │ │ │ ├── compile.cpython-312.pyc
│ │ │ │ ├── signatures.cpython-312.pyc
│ │ │ │ ├── validations.cpython-312.pyc
│ │ │ ├── compiled
│ │ │ │ ├── intent_classifier.json
│ │ │ │ ├── rag.json
│ │ │ ├── lm_clients
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── llama3_8b.cpython-312.pyc
│ │ │ │ ├── llama3_8b.py
│ │ │ ├── modules
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── chatbot.cpython-312.pyc
│ │ │ │ │ ├── intent_classifier.cpython-312.pyc
│ │ │ │ │ ├── rag.cpython-312.pyc
│ │ │ │ │ ├── simplified_baleen.cpython-312.pyc
│ │ │ │ ├── chatbot.py
│ │ │ │ ├── intent_classifier.py
│ │ │ │ ├── rag.py
│ │ │ │ ├── simplified_baleen.py
│ │ │ ├── optimizers
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── compile.cpython-312.pyc
│ │ │ │ │ ├── intent_classifier.cpython-312.pyc
│ │ │ │ │ ├── rag.cpython-312.pyc
│ │ │ │ ├── intent_classifier.py
│ │ │ │ ├── rag.py
│ │ │ ├── signatures
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── signatures.cpython-312.pyc
│ │ │ │ ├── signatures.py
│ │ │ ├── utils
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── download_dataset.cpython-312.pyc
│ │ │ │ │ ├── initialize_DSPy.cpython-312.pyc
│ │ │ │ │ ├── load_compiled_module.cpython-312.pyc
│ │ │ │ │ ├── load_dataset.cpython-312.pyc
│ │ │ │ │ ├── print_history.cpython-312.pyc
│ │ │ │ ├── initialize_DSPy.py
│ │ │ │ ├── load_compiled_module.py
│ │ │ │ ├── load_dataset.py
│ │ │ │ ├── print_history.py
│ │ │ ├── validations
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── validations.cpython-312.pyc
│ │ │ │ ├── validations.py
│ │ ├── langchain
│ │ │ ├── .DS_Store
│ │ │ ├── __pycache__
│ │ │ │ ├── common.cpython-312.pyc
│ │ │ │ ├── langgraph_main.cpython-312.pyc
│ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ ├── main_graph.cpython-312.pyc
│ │ │ │ ├── reply_chat.cpython-312.pyc
│ │ │ │ ├── schema.cpython-312.pyc
│ │ │ ├── common.py
│ │ │ ├── conditional_edges
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── pick_by_llm.cpython-312.pyc
│ │ │ │ │ ├── simple_check.cpython-312.pyc
│ │ │ │ ├── llm
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── plan.cpython-312.pyc
│ │ │ │ │ │ ├── routers.cpython-312.pyc
│ │ │ │ │ ├── check.py
│ │ │ │ │ ├── reflect.py
│ │ │ │ ├── non_llm
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── routers.cpython-312.pyc
│ │ │ │ │ │ ├── simple_check.cpython-312.pyc
│ │ │ │ │ ├── simple_check.py
│ │ │ │ ├── old_edges.py
│ │ │ ├── main_graph.py
│ │ │ ├── nodes
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── check.cpython-312.pyc
│ │ │ │ │ ├── decide.cpython-312.pyc
│ │ │ │ │ ├── generate.cpython-312.pyc
│ │ │ │ │ ├── state_control.cpython-312.pyc
│ │ │ │ │ ├── update.cpython-312.pyc
│ │ │ │ ├── llm
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── criticize.cpython-312.pyc
│ │ │ │ │ │ ├── decide.cpython-312.pyc
│ │ │ │ │ │ ├── extract.cpython-312.pyc
│ │ │ │ │ │ ├── find.cpython-312.pyc
│ │ │ │ │ │ ├── generate.cpython-312.pyc
│ │ │ │ │ │ ├── pick.cpython-312.pyc
│ │ │ │ │ │ ├── plan.cpython-312.pyc
│ │ │ │ │ ├── criticize.py
│ │ │ │ │ ├── decide.py
│ │ │ │ │ ├── extract.py
│ │ │ │ │ ├── find.py
│ │ │ │ │ ├── generate.py
│ │ │ │ │ ├── pick.py
│ │ │ │ │ ├── update.py
│ │ │ │ ├── non_llm
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── gather_context.cpython-312.pyc
│ │ │ │ │ │ ├── predefined_reply.cpython-312.pyc
│ │ │ │ │ │ ├── state_control.cpython-312.pyc
│ │ │ │ │ ├── gather_context.py
│ │ │ │ │ ├── neo4j_graph_query.py
│ │ │ │ │ ├── predefined_reply.py
│ │ │ │ │ ├── state_control.py
│ │ │ │ │ ├── tournament_stage.py
│ │ │ │ ├── old_nodes.py
│ │ │ ├── schema.py
│ │ │ ├── subgraphs
│ │ │ │ ├── end_of_chat
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ │ ├── graph.py
│ │ │ │ ├── middle_of_chat
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ │ ├── extract
│ │ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ │ ├── graph.py
│ │ │ │ │ ├── gather_context
│ │ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ │ │ ├── graph.py
│ │ │ │ │ ├── graph.py
│ │ │ │ │ ├── graph_agent
│ │ │ │ │ │ ├── graph.py
│ │ │ │ ├── start_of_chat
│ │ │ │ │ ├── __pycache__
│ │ │ │ │ │ ├── graph.cpython-312.pyc
│ │ │ │ │ │ ├── main.cpython-312.pyc
│ │ │ │ │ ├── graph.py
│ │ │ │ ├── utils
│ │ │ │ │ ├── tournament.py
│ │ │ ├── utils
│ │ │ │ ├── __pycache__
│ │ │ │ │ ├── converters.cpython-312.pyc
│ │ │ │ │ ├── messages_to_string.cpython-312.pyc
│ │ │ │ ├── converters.py
│ │ │ │ ├── neo4j.py
│ │ ├── local_llms
│ │ │ ├── .DS_Store
│ │ │ ├── __pycache__
│ │ │ │ ├── llama3_8b.cpython-312.pyc
│ │ │ │ ├── llama3_8b_on_vllm.cpython-312.pyc
│ │ │ ├── llama3_8b.py
│ │ │ ├── llama3_8b_on_tensorRT.py
│ │ │ ├── llama3_8b_on_vllm.py
│ │ ├── main.py
│ │ ├── public
│ │ │ ├── __pycache__
│ │ │ │ ├── questions.cpython-312.pyc
│ │ │ ├── questions.py
│ │ ├── schemas
│ │ │ ├── __pycache__
│ │ │ │ ├── schemas.cpython-312.pyc
│ │ │ ├── schemas.py
│ │ ├── test_notebooks
│ │ │ ├── .DS_Store
│ │ │ ├── __pycache__
│ │ │ │ ├── tweet_metric.cpython-312.pyc
│ │ │ ├── cache.db
│ │ │ ├── compiling_langchain.ipynb
│ │ │ ├── conditional_edges_test.ipynb
│ │ │ ├── langgraph_dspy.ipynb
│ │ │ ├── parallel_node.ipynb
│ │ │ ├── pydantic_test.ipynb
│ │ │ ├── stable_sorting.ipynb
│ │ │ ├── trainset.json
│ │ │ ├── tweet_metric.py
│ │ ├── utils
│ │ │ ├── .DS_Store
│ │ │ ├── __pycache__
│ │ │ │ ├── default_questions.cpython-312.pyc
│ │ │ │ ├── default_topics.cpython-312.pyc
│ │ │ │ ├── dspy_initialize.cpython-312.pyc
│ │ │ │ ├── mongodb.cpython-312.pyc
│ │ │ │ ├── twilio.cpython-312.pyc
│ │ │ ├── mongodb.py
│ │ │ ├── twilio.py
│ ├── graph_imgs
│ │ ├── main_graph.png
│ │ ├── middle_of_chat.png
│ │ ├── tournament.png
│ ├── readme.md
│ ├── requirements.txt
├── frontend
│ ├── .DS_Store
│ ├── .eslintrc.json
│ ├── .gitignore
│ ├── NOTICE
│ ├── README.md
│ ├── app
│ │ ├── (chat)
│ │ │ ├── chat
│ │ │ │ ├── [id]
│ │ │ │ │ ├── page.tsx
│ │ │ ├── layout.tsx
│ │ │ ├── page.tsx
│ │ ├── .DS_Store
│ │ ├── actions.ts
│ │ ├── api
│ │ │ ├── auth
│ │ │ │ ├── callback
│ │ │ │ │ ├── google
│ │ │ │ │ │ ├── route.ts
│ │ ├── globals.css
│ │ ├── layout.tsx
│ │ ├── login
│ │ │ ├── actions.ts
│ │ │ ├── page.tsx
│ │ ├── new
│ │ │ ├── page.tsx
│ │ ├── reviews
│ │ │ ├── layout.tsx
│ │ │ ├── page.tsx
│ │ │ ├── review
│ │ │ │ ├── [id]
│ │ │ │ │ ├── page.tsx
│ │ ├── share
│ │ │ ├── [id]
│ │ │ │ ├── page.tsx
│ │ ├── signup
│ │ │ ├── actions.ts
│ │ │ ├── page.tsx
│ ├── auth.config.ts
│ ├── auth.ts
│ ├── components
│ │ ├── .DS_Store
│ │ ├── button-scroll-to-bottom.tsx
│ │ ├── chat-history.tsx
│ │ ├── chat-list.tsx
│ │ ├── chat-message-actions.tsx
│ │ ├── chat-message.tsx
│ │ ├── chat-panel.tsx
│ │ ├── chat-share-dialog.tsx
│ │ ├── chat.tsx
│ │ ├── clear-history.tsx
│ │ ├── empty-screen.tsx
│ │ ├── external-link.tsx
│ │ ├── footer.tsx
│ │ ├── header.tsx
│ │ ├── login-button.tsx
│ │ ├── login-form.tsx
│ │ ├── markdown.tsx
│ │ ├── prompt-form.tsx
│ │ ├── providers.tsx
│ │ ├── review-card.tsx
│ │ ├── sidebar-actions.tsx
│ │ ├── sidebar-desktop.tsx
│ │ ├── sidebar-footer.tsx
│ │ ├── sidebar-item.tsx
│ │ ├── sidebar-items.tsx
│ │ ├── sidebar-list.tsx
│ │ ├── sidebar-mobile.tsx
│ │ ├── sidebar-toggle.tsx
│ │ ├── sidebar.tsx
│ │ ├── signup-form.tsx
│ │ ├── stocks
│ │ │ ├── events-skeleton.tsx
│ │ │ ├── events.tsx
│ │ │ ├── google-map-picker.tsx
│ │ │ ├── index.tsx
│ │ │ ├── message.tsx
│ │ │ ├── pick-vendor.tsx
│ │ │ ├── spinner.tsx
│ │ │ ├── stock-purchase.tsx
│ │ │ ├── stock-skeleton.tsx
│ │ │ ├── stock.tsx
│ │ │ ├── stocks-skeleton.tsx
│ │ │ ├── stocks.tsx
│ │ ├── tailwind-indicator.tsx
│ │ ├── theme-toggle.tsx
│ │ ├── ui
│ │ │ ├── alert-dialog.tsx
│ │ │ ├── badge.tsx
│ │ │ ├── button.tsx
│ │ │ ├── card.tsx
│ │ │ ├── codeblock.tsx
│ │ │ ├── dialog.tsx
│ │ │ ├── dropdown-menu.tsx
│ │ │ ├── icons.tsx
│ │ │ ├── input.tsx
│ │ │ ├── label.tsx
│ │ │ ├── select.tsx
│ │ │ ├── separator.tsx
│ │ │ ├── sheet.tsx
│ │ │ ├── sonner.tsx
│ │ │ ├── switch.tsx
│ │ │ ├── textarea.tsx
│ │ │ ├── tooltip.tsx
│ │ ├── user-menu.tsx
│ ├── components.json
│ ├── lib
│ │ ├── .DS_Store
│ │ ├── chat
│ │ │ ├── actions.tsx
│ │ ├── hooks
│ │ │ ├── use-copy-to-clipboard.tsx
│ │ │ ├── use-enter-submit.tsx
│ │ │ ├── use-local-storage.ts
│ │ │ ├── use-scroll-anchor.tsx
│ │ │ ├── use-sidebar.tsx
│ │ │ ├── use-streamable-text.ts
│ │ ├── mongodb.ts
│ │ ├── types.ts
│ │ ├── utils.ts
│ ├── middleware.ts
│ ├── next-env.d.ts
│ ├── next.config.js
│ ├── package-lock.json
│ ├── package.json
│ ├── pnpm-lock.yaml
│ ├── postcss.config.js
│ ├── prettier.config.cjs
│ ├── public
│ │ ├── apple-touch-icon.png
│ │ ├── ernest_logo.png
│ │ ├── favicon-16x16.png
│ │ ├── favicon.ico
│ ├── tailwind.config.ts
│ ├── tsconfig.json
├── scripts
│ ├── Graph_RAG_example.ipynb
│ ├── RAG.ipynb
│ ├── chroma_test.ipynb
│ ├── graph_database_for_langchain.ipynb
│ ├── graph_database_test_neo4j.ipynb
│ ├── graph_database_test_whyhow copy.ipynb
│ ├── graph_legend.png
│ ├── graph_visualization.png
│ ├── langchain_review.csv
│ ├── langchain_review.txt
│ ├── langchain_review_topic.csv
│ ├── langchain_review_topic.json
│ ├── langchain_reviews.txt
│ ├── review_preprocessing.ipynb
│ ├── sample_pdf.pdf
│ ├── scrapped_reviews
│ │ ├── reviews.csv
│ │ ├── reviews_selected.csv
│ │ ├── reviews_selected_schema.json
│ │ ├── reviews_selected_small.csv
│ │ ├── reviews_selected_small_topics.csv
│ │ ├── salon_list.csv
│ │ ├── vectorized
│ │ │ ├── chroma.sqlite3
│ │ │ ├── edd934fe-37ac-44cf-ac8e-32b8695eb5e6
│ │ │ │ ├── data_level0.bin
│ │ │ │ ├── header.bin
│ │ │ │ ├── index_metadata.pickle
│ │ │ │ ├── length.bin
│ │ │ │ ├── link_lists.bin
│ ├── topic_list.json
│ ├── vectorstore
│ │ ├── 7a848e91-b158-44d7-9dfb-8f0ee773e46f
│ │ │ ├── data_level0.bin
│ │ │ ├── header.bin
│ │ │ ├── length.bin
│ │ │ ├── link_lists.bin
│ │ ├── chroma.sqlite3
""",
        "steps": [],
        "analysis_results": [],
        "validate_count": 0,
    }
    state = retrieve_code_snippets(state)
    print(f"==>> Updated state: {state}")
