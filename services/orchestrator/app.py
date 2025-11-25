from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MEMMCP_HTTP_URL = os.getenv("MEMMCP_HTTP_URL", "http://memorymcp-http:59081/mcp")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://langfuse:3000")
LANGFUSE_API_KEY = os.getenv("LANGFUSE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("ORCH_QDRANT_COLLECTION", "memmcp_notes")

MCP_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2024-11-05",
    "MCP-Transport": "streamable-http",
}

app = FastAPI(title="memMCP orchestrator", version="0.1.0")


class MemoryWrite(BaseModel):
    projectName: str = Field(..., description="Project identifier")
    fileName: str = Field(..., description="File name inside the project")
    content: str = Field(..., description="Payload to store")


class TrajectoryIngest(BaseModel):
    project: str
    summary: str
    trajectory: dict[str, Any]


async def _call_mcp(payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(MEMMCP_HTTP_URL, json=payload, headers=MCP_HEADERS)
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)
    data = None
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
    if not data:
        raise HTTPException(500, "No MCP response data")
    if "error" in data:
        raise HTTPException(500, f"MCP error: {data['error']}")
    return data["result"]


async def call_memory_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    return await _call_mcp(payload)


async def list_projects() -> list[str]:
    result = await call_memory_tool("list_projects", {})
    return result.get("content", [])


async def list_files(project: str) -> list[str]:
    result = await call_memory_tool("list_project_files", {"projectName": project})
    return result.get("content", [])


async def ensure_qdrant_collection() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}")
    if resp.status_code == 200:
        return
    schema = {
        "vectors": {"size": 32, "distance": "Cosine"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        create = await client.put(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}", json=schema
        )
    if create.status_code not in (200, 202):
        raise RuntimeError(f"Failed to create Qdrant collection: {create.text}")


def _cheap_embedding(text: str) -> list[float]:
    # Deterministic toy embedding based on character codes (placeholder until a real model is plugged in)
    base = [0.0] * 32
    for idx, char in enumerate(text.encode("utf-8")):
        base[idx % 32] += char / 255.0
    norm = max(sum(base), 1e-6)
    return [round(val / norm, 6) for val in base]


async def push_to_qdrant(project: str, file_name: str, content: str) -> None:
    await ensure_qdrant_collection()
    payload = {
        "points": [
            {
                "id": str(uuid.uuid4()),
                "vector": _cheap_embedding(content),
                "payload": {
                    "project": project,
                    "file": file_name,
                    "summary": content[:500],
                },
            }
        ]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.put(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points",
            json=payload,
        )
    if resp.status_code not in (200, 202):
        raise RuntimeError(f"Qdrant upsert failed: {resp.text}")


async def push_to_langfuse(project: str, summary: str, payload: dict[str, Any]) -> None:
    if not LANGFUSE_API_KEY:
        return
    event = {
        "id": str(uuid.uuid4()),
        "type": "trace",
        "name": project,
        "metadata": {"summary": summary},
        "input": payload,
    }
    headers = {"x-langfuse-api-key": LANGFUSE_API_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(f"{LANGFUSE_URL}/api/public/ingest", json=[event], headers=headers)


@app.get("/projects")
async def get_projects():
    projects = await list_projects()
    results = []
    for project in projects:
        files = await list_files(project)
        results.append({"name": project, "files": [{"name": f} for f in files]})
    return {"projects": results}


@app.get("/projects/{project}/files")
async def get_files(project: str):
    files = await list_files(project)
    return {"files": files}


@app.post("/memory/write")
async def write_memory(payload: MemoryWrite):
    await call_memory_tool(
        "memory_bank_write",
        payload.model_dump(),
    )
    await asyncio.gather(
        push_to_qdrant(payload.projectName, payload.fileName, payload.content),
        push_to_langfuse(payload.projectName, "manual entry", payload.model_dump()),
    )
    return {"ok": True}


@app.post("/ingest/trajectory")
async def ingest_trajectory(body: TrajectoryIngest):
    summary = body.summary
    await call_memory_tool(
        "memory_bank_write",
        {
            "projectName": body.project,
            "fileName": f"trajectory-{uuid.uuid4().hex}.json",
            "content": json.dumps(body.trajectory, indent=2),
        },
    )
    await asyncio.gather(
        push_to_qdrant(body.project, "trajectory", summary),
        push_to_langfuse(body.project, summary, body.trajectory),
    )
    return {"ok": True}


@app.get("/status")
async def status():
    services = []
    # memory bank check
    try:
        await list_projects()
        services.append({"name": "memory-bank", "healthy": True, "detail": "MCP reachable"})
    except Exception as exc:  # pragma: no cover - health fallback
        services.append({"name": "memory-bank", "healthy": False, "detail": str(exc)})

    # Langfuse
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(LANGFUSE_URL)
        services.append({
            "name": "langfuse",
            "healthy": resp.status_code == 200,
            "detail": f"status {resp.status_code}",
        })
    except Exception as exc:  # pragma: no cover
        services.append({"name": "langfuse", "healthy": False, "detail": str(exc)})

    # Qdrant
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{QDRANT_URL}/readyz")
        services.append({
            "name": "qdrant",
            "healthy": resp.status_code == 200,
            "detail": f"status {resp.status_code}",
        })
    except Exception as exc:  # pragma: no cover
        services.append({"name": "qdrant", "healthy": False, "detail": str(exc)})

    return {"services": services}
