import os
import json
import pickle
from varname import nameof as n

from langchain_openai import OpenAIEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS

from ..state_schema import State

from ..utils.semantic_splitter import semantic_code_splitter


def retrieve_code_snippets(state: State):
    print("Retrieving code snippets for ", state["title"])
    hypothesis_json = state["messages"][-1]
    hypothesis_dict = json.loads(hypothesis_json.content)
    queries = hypothesis_dict["queries"][:3] #! only use top 3 queries for now

    if os.path.exists(f"./cache/documents/{state['title'].replace('/', '_')}.pkl") and os.path.exists(f"./cache/embeddings/{state['title'].replace('/', '_')}.pkl"):
        print("Loading cached documents and embeddings")
        with open(f"./cache/documents/{state['title'].replace('/', '_')}.pkl", "rb") as f:
            documents = pickle.load(f)
        with open(f"./cache/embeddings/{state['title'].replace('/', '_')}.pkl", "rb") as f:
            embeddings = pickle.load(f)
    else:
        embeddings, documents = semantic_code_splitter(state["repo_root_path"])
        
        os.makedirs("./cache/documents", exist_ok=True)
        with open(f"./cache/documents/{state['title'].replace('/', '_')}.pkl", "wb") as f:
            pickle.dump(documents, f)

        os.makedirs("./cache/embeddings", exist_ok=True)
        with open(f"./cache/embeddings/{state['title'].replace('/', '_')}.pkl", "wb") as f:
            pickle.dump(embeddings, f)

    # BM25
    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 2

    # FAISS
    embedding = OpenAIEmbeddings()
    faiss_vectorstore = FAISS.from_documents(
        documents, embedding
    )
    faiss_retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 2})

    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5]
    )
    retrieved_code_snippets = []
    for query in queries:
        result = ensemble_retriever.invoke(query)
        retrieved_code_snippets.extend(result)

    print(f"Retrieved {len(retrieved_code_snippets)} code snippets")

    formatted_snippets = [
        f"{document.metadata['source']}:\n{document.page_content}"
        for document in retrieved_code_snippets
    ]

    return {
        "retrieved_code_snippets": "\n\n\n".join(formatted_snippets)
    }
