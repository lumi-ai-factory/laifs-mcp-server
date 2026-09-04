import logging
import os
import requests
import time

from fastmcp import FastMCP
from pydantic import Field
from qdrant_client import QdrantClient
from typing import Annotated

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore


class LumiServiceStatus:
    def __init__(self, interval: float = 2.0):
        self.interval = interval
        self.session = requests.Session()

        self.last_status_check = 0
        self.status = None

    def get_status(self):
        current_time = time.time()

        if current_time - self.last_status_check >= self.interval:
            self.status = self.session.get("https://status.lumi.csc.fi/api/status")
            self.last_status_check = current_time

        return self.status


logger = logging.getLogger(__name__)

client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT__SERVICE__READ_ONLY_API_KEY"],
)

embedding = FastEmbedEmbeddings(model_name=os.environ["EMBEDDING_MODEL"])

while not client.collection_exists(os.environ["COLLECTION_NAME"]):
    logger.warning(
        f"Collection '{os.environ['COLLECTION_NAME']}' not found. "
        f"Retrying in {os.environ['COLLECTION_POLL_INTERVAL']} seconds..."
    )
    time.sleep(int(os.environ["COLLECTION_POLL_INTERVAL"]))

vector_store = QdrantVectorStore(
    client=client,
    collection_name=os.environ["COLLECTION_NAME"],
    embedding=embedding,
)

service_status = LumiServiceStatus()

mcp = FastMCP(name=os.environ["SERVER_NAME"], mask_error_details=True)


@mcp.tool()
def retrieve_docs(
    query: Annotated[
        str, Field(min_length=1, max_length=100)
    ],
    k: Annotated[
        int, Field(description="Number of documents to return", ge=1, le=10),
    ] = 4,
) -> list[dict]:
    """Search LUMI documentation and return the most relevant passages."""
    results = vector_store.similarity_search_with_score(query=query, k=k)

    docs = [
        {
            "page_content": doc.page_content,
            "source": doc.metadata["source"],
            "score": score,
        }
        for doc, score in results
    ]

    return docs


@mcp.tool()
def get_service_status() -> dict | str:
    """Get the status of LUMI and related services."""
    return service_status.get_status().json()


def main():
    mcp.run(transport="http", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
