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
    def __init__(self, check_interval: float = 2.0):
        self.base_url = "https://status.lumi.csc.fi/api/"
        self.session = requests.Session()

        self.check_interval = check_interval

        self.data = {
            "status": {"last_check": 0, "response": None},
            "maintenance": {"last_check": 0, "response": None},
            "incidents": {"last_check": 0, "response": None},
        }

    def fetch(self, query: str = "status") -> dict | list:
        current_time = time.time()

        if current_time - self.data[query]["last_check"] >= self.check_interval:
            self.data[query]["response"] = self.session.get(self.base_url + query)
            self.data[query]["last_check"] = current_time

        return self.data[query]["response"]


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
def get_service_status(
    query: Annotated[
        str, Field(description="'status, 'maintenance' or 'incidents'"),
    ] = "status"
) -> dict | str:
    """Get status information on LUMI and related services.
    * status - overall status, node availability, response time
    * maintenance - information on outages due to maintenance
    * incidents - information on outages due to incidents
    """
    if query not in service_status.data.keys():
        return (
            f"Unknown query '{query}'. "
            "Recognized values are 'status', 'maintenance' and 'incidents'."
        )
    return service_status.fetch(query).json()


def main():
    mcp.run(transport="http", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
