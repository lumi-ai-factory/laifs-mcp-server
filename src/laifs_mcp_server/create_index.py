#!/usr/bin/env python3

import argparse
import json
import os
import subprocess

os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

from pathlib import Path
from transformers import AutoTokenizer
from uuid import uuid4

from langchain_community.document_loaders import DirectoryLoader
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_text_splitters.base import TokenTextSplitter
from langchain_qdrant import QdrantVectorStore

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

DEFAULT_GLOB = "*.md"


def update_metadata(docs: list, base_path: Path, remote: str):
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        cwd=base_path,
        check=True,
        text=True,
    ).stdout.strip()

    source_prefix = remote.removesuffix(".git") + "/blob/" + commit

    for doc in docs:
        file_path = Path(doc.metadata["source"])
        doc.metadata["source"] = source_prefix + "/" + str(file_path.relative_to(base_path))


def load_documents(docs_path: Path, base_path: Path, remote: str, glob: str):
    loader = DirectoryLoader(
        path=docs_path,
        glob=glob,
        recursive=True,
        show_progress=True,
    )

    docs = loader.load()
    update_metadata(docs, base_path=base_path, remote=remote)

    return docs


def split_documents(docs, model_name, chunk_size, chunk_overlap):
    text_splitter = TokenTextSplitter.from_huggingface_tokenizer(
        tokenizer=AutoTokenizer.from_pretrained(model_name),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks = text_splitter.split_documents(docs)

    return chunks


def init_vector_store(url, api_key, collection_name, vector_size, model_name):
    client = QdrantClient(url=url, api_key=api_key)

    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
        print(f"Deleted old collection '{collection_name}'")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"Created new collection '{collection_name}'")

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=FastEmbedEmbeddings(model_name=model_name),
    )

    return vector_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("docs_root", help="Path to directory containing docs to index")
    parser.add_argument("config_file", help="JSON config file with indexing parameters")
    parser.add_argument("--model-name", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--vector-size", type=int, default=384)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--chunk-overlap", type=int, default=16)
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--qdrant-api-key", default=None)
    parser.add_argument("--collection-name", default="lumi_documentation")
    args = parser.parse_args()

    with open(args.config_file) as f:
        config = json.load(f)

    print("Loading documents...")
    all_docs = []
    for repo in config:
        base_path = Path(args.docs_root) / repo.get("name")
        docs_path = base_path / (repo.get("subdir") or "")

        docs = load_documents(
            docs_path=docs_path,
            base_path=base_path,
            remote=repo.get("remote"),
            glob=repo.get("glob") or DEFAULT_GLOB,
        )

        all_docs += docs
        print(f"Loaded {len(docs)} documents from {base_path}")
    print(f"Total documents loaded: {len(all_docs)}")

    chunks = split_documents(
        all_docs, model_name=args.model_name,
        chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap,
    )
    print(f"Split {len(all_docs)} documents into {len(chunks)} chunks")

    vector_store = init_vector_store(
        url=args.qdrant_url,
        api_key=args.qdrant_api_key,
        collection_name=args.collection_name,
        vector_size=args.vector_size,
        model_name=args.model_name,
    )

    print("Indexing chunks...")
    vector_store.add_documents(
        documents=chunks,
        ids=[str(uuid4()) for _ in range(len(chunks))],
    )
    print("Done!")


if __name__ == "__main__":
    main()
