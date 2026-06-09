#!/bin/bash

set -eu

DATA_DIR=
QDRANT_API_KEY=your_secret_api_key_here

rm -rf data/docs && mkdir -p data/docs
git clone https://github.com/Lumi-supercomputer/LUMI-AI-Guide.git data/docs/LUMI-AI-Guide
git clone https://github.com/Lumi-supercomputer/lumi-userguide.git data/docs/lumi-userguide

curl -X DELETE \
    "http://localhost:6333/collections/lumi_documentation" \
    --header "api-key: $QDRANT_API_KEY"

index-docs data/docs/LUMI-AI-Guide \
    --qdrant-api-key $QDRANT_API_KEY
index-docs data/docs/lumi-userguide \
    --docs-dir docs \
    --qdrant-api-key $QDRANT_API_KEY
