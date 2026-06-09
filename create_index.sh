#!/bin/bash

set -euo pipefail

DOCS_ROOT=data/docs
CONFIG_FILE=config/index.json
QDRANT_API_KEY=your_secret_api_key_here

rm -rf "$DOCS_ROOT" && mkdir -p "$DOCS_ROOT"

for remote in $(jq -r .[].remote "$CONFIG_FILE"); do
    git clone "$remote" "$DOCS_ROOT/$(basename $remote .git)"
done

index-docs "$DOCS_ROOT" config/index.json --qdrant-api-key $QDRANT_API_KEY
