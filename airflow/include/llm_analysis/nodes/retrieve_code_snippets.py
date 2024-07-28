import os
import json
import pickle
import numpy as np
from varname import nameof as n
from sklearn.metrics.pairwise import cosine_similarity

from langchain_core.documents.base import Document
from langchain_openai import OpenAIEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)

from ..state_schema import State


def retrieve_code_snippets(state: State):
    hypothesis_json = state["messages"][-1]
    hypothesis_dict = json.loads(hypothesis_json)
    hypothesis = hypothesis_dict["hypothesis"]
    print(f"==>> hypothesis: {hypothesis}")
    root_path = state["repo_root_path"]

    #TODO: Cache documents
    # Load and split documents
    document_path = "/Users/minkijung/Documents/2PetProjects/ernest/backend/app/langchain/conditional_edges/llm"
    loader = DirectoryLoader(
        document_path, glob=["*.md", "*.py"], loader_cls=TextLoader, recursive=True
    )
    documents = loader.load()
    print(f"==>> Total document loaded: {len(documents)}")

    if not documents:
        print("No documents found in the specified directory.")
        raise Exception("No documents found in the specified directory.")

    # Seperators: ['\nclass ', '\ndef ', '\n\tdef ', '\n\n', '\n', ' ', '']
    python_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=200,
        chunk_overlap=0,
        keep_separator="end",
        strip_whitespace=False
    )
    documents = python_splitter.split_documents(documents)

    use_cache = False
    if not use_cache:
        openAIEmbedding = OpenAIEmbeddings()
        embeddings = openAIEmbedding.embed_documents(
                [document.page_content for document in documents]
            )

        # Save embeddings to a local file
        embedding_file = "embeddings.pkl"
        with open(embedding_file, "wb") as f:
            pickle.dump(embeddings, f)
        print(f"Embeddings saved to {embedding_file}")
    else:
        # Load embeddings from the local file
        embedding_file = "embeddings.pkl"
        if os.path.exists(embedding_file):
            with open(embedding_file, "rb") as f:
                embeddings = pickle.load(f)
            print(f"Embeddings loaded from {embedding_file}")
        else:
            print(f"Embedding file {embedding_file} not found.")

    print(f"Number of loaded embeddings: {len(embeddings)}")

    # group documents with the same metadata source value
    documents_by_source = {}
    for doc, embedding in zip(documents, embeddings):
        source = doc.metadata["source"]
        if source not in documents_by_source:
            documents_by_source[source] = []
        documents_by_source[source].append(
            {"content": doc.page_content, "embedding": embedding}
        )

    print("Caculating semantic similarities...")
    cosine_similarities = []
    for source, docs_in_same_source in documents_by_source.items():
        cosine_similarities_per_source = {"source": source, "similarities": []}
        print(f"Source: {source}")
        print(f"Number of docs_in_same_source: {len(docs_in_same_source)}")
        for i in range(len(docs_in_same_source) - 1):
            cosine_similarity_result = cosine_similarity(
                [docs_in_same_source[i]["embedding"]],
                [docs_in_same_source[i + 1]["embedding"]],
            )
            cosine_similarities_per_source["similarities"].append(
                cosine_similarity_result[0][0]
            )
        cosine_similarities.append(cosine_similarities_per_source)

    documents_after_semantic_merging = []
    for (source, document), cosine_similarities_per_source in zip(
        documents_by_source.items(), cosine_similarities
    ):
        if source != cosine_similarities_per_source["source"]:
            print(
                f"Source mismatch: {source} vs {cosine_similarities_per_source['source']}"
            )
            raise Exception("Source mismatch")

        merged_chunk = ""
        for idx, similarity in enumerate(
            cosine_similarities_per_source["similarities"]
        ):
            # print(f"Similarity between {idx} and {idx+1}: {similarity}")
            # print("sentence 1: ", document[idx]["content"])
            # print("sentence 2: ", document[idx+1]["content"])
            # print("-------------------------------------------------")
            if similarity > 0.7:
                if len(merged_chunk) == 0:
                    merged_chunk = (
                        document[idx]["content"] + document[idx + 1]["content"]
                    )
                else:
                    merged_chunk += document[idx + 1]["content"]
            else:
                documents_after_semantic_merging.append(Document(merged_chunk, metadata={"source": source}))

    print(f"documents_after_semantic_merging: {len(documents_after_semantic_merging)}")
    print(f"documents_after_semantic_merging: {documents_after_semantic_merging}")

    # BM25
    bm25_retriever = BM25Retriever.from_documents(documents_after_semantic_merging)
    bm25_retriever.k = 1

    # FAISS
    embedding = OpenAIEmbeddings()
    faiss_vectorstore = FAISS.from_documents(
        documents_after_semantic_merging, embedding
    )
    faiss_retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 1})

    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5]
    )

    docs = ensemble_retriever.invoke("Check if the message is cutoff")
    for doc in docs:
        print("------------RESULT-------------")
        print(doc.metadata["source"])
        print(doc.page_content)

    return
