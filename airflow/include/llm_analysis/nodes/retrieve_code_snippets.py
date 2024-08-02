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


def retrieve_code_by_hybrid_search_with_queries(state: State):
    print("Retrieving code snippets for ", state["title"])
    hypothesis_json = state["messages"][-1]
    hypothesis_dict = json.loads(hypothesis_json.content)
    queries = hypothesis_dict["queries"][:3]  #! only use top 3 queries for now

    if os.path.exists(f"./cache/documents/{state['title']}.pkl") and os.path.exists(
        f"./cache/faiss_vectorstore/{state['title']}.pkl"
    ):
        print("Loading cached documents and embeddings")
        with open(f"./cache/documents/{state['title']}.pkl", "rb") as f:
            documents = pickle.load(f)
        embedding = OpenAIEmbeddings(model="text-embedding-3-large")
        faiss_vectorstore = FAISS.load_local(
            f"./cache/faiss_vectorstore/{state['title']}.pkl",
            embedding,
            allow_dangerous_deserialization=True,
        )
    else:
        documents = semantic_code_splitter(state["repo_root_path"])

        os.makedirs("./cache/documents", exist_ok=True)
        with open(f"./cache/documents/{state['title']}.pkl", "wb") as f:
            pickle.dump(documents, f)

        print(f"Creating FAISS vectorstore for {len(documents)} documents")
        embedding = OpenAIEmbeddings(model="text-embedding-3-large")
        faiss_vectorstore = FAISS.from_documents(documents, embedding)

        faiss_vectorstore.save_local(f"./cache/faiss_vectorstore/{state['title']}.pkl")

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 2

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
        "retrieved_code_snippets": {
            "sources": [
                document.metadata["source"] for document in retrieved_code_snippets
            ],
            "content": "\n\n------------\n\n".join(formatted_snippets),
        }
    }
