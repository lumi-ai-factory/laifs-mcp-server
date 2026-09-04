FROM python:3.13-slim

WORKDIR /mcp

RUN --mount=type=bind,target=. pip install --no-cache-dir .

EXPOSE 8000

CMD ["run-server"]
