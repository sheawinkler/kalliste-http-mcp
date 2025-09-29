FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir mcp-server-qdrant
CMD ["mcp-server-qdrant","--transport","streamable-http","--host","0.0.0.0","--port","8002"]
