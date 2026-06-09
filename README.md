# LUMI AI Factory MCP Server

This repository contains the source code of the
[LUMI AI Factory MCP server](https://docs.lumi-supercomputer.eu/laif/software/agent-infrastructure/#mcp-server)
hosted at <https://lumi-aif-agents.2.rahtiapp.fi/mcp>. Additionally, there is a `Dockerfile` and a
`compose.yaml` file that can be used for deploying a local development instance.

## Development instance

This section explains how to deploy a local development instance of the MCP server. Deploying the
server requires a working installation of Docker and Python 3.11 or higher.

Start the Qdrant vector database and the MCP server with Docker Compose.

```bash
# Docker requires root privileges by default,
# so you may need to run the command with `sudo`
docker compose up
```

Create a vector index for document retrieval.

```bash
# Create and activate virtual environment
python3 -m venv .venv
. .venv/bin/activate

# Install the Python project in the virtual environment
pip install -e .[index]

# Create the index
bash create_index.sh
```

Finally, test the server using the `fastmcp` CLI tool.

```bash
fastmcp call http://localhost:8000/mcp retrieve_docs query='agent infrastructure' k=1
```
