from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MEMMCP_HTTP_URL = os.getenv("MEMMCP_HTTP_URL", "http://memorymcp-http:59081/mcp")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://langfuse:3000")
LANGFUSE_API_KEY = os.getenv("LANGFUSE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("ORCH_QDRANT_COLLECTION", "memmcp_notes")

EMBEDDING_PROVIDER = os.getenv("ORCH_EMBED_PROVIDER", os.getenv("EMBEDDING_PROVIDER", "cheap")).lower()
EMBEDDING_MODEL = os.getenv("ORCH_EMBED_MODEL", os.getenv("EMBEDDING_MODEL", "nomic-embed-text"))
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", os.getenv("OPENAI_API_BASE"))
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", os.getenv("OPENAI_API_KEY"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
FALLBACK_EMBED_DIM = int(os.getenv("ORCH_EMBED_DIM", os.getenv("EMBEDDING_DIM", "32")))
TRADING_HISTORY_LIMIT = int(os.getenv("TRADING_HISTORY_LIMIT", "256"))
TRADING_HISTORY_PATH = Path(
    os.getenv(
        "TRADING_HISTORY_PATH",
        str(Path(__file__).resolve().parent / "data" / "trading_metrics.ndjson"),
    )
)
STRATEGY_HISTORY_LIMIT = int(os.getenv("STRATEGY_HISTORY_LIMIT", "256"))
STRATEGY_HISTORY_PATH = Path(
    os.getenv(
        "STRATEGY_HISTORY_PATH",
        str(Path(__file__).resolve().parent / "data" / "strategy_metrics.ndjson"),
    )
)

MCP_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2024-11-05",
    "MCP-Transport": "streamable-http",
}


class OrchestratorError(RuntimeError):
    """Intentional failure we can bubble up with a helpful hint."""


def _cheap_embedding(text: str, vector_size: int) -> list[float]:
    """Cheap deterministic embedding used when no provider is configured."""

    base = [0.0] * vector_size
    encoded = text.encode("utf-8")
    if not encoded:
        return base
    for idx, char in enumerate(encoded):
        base[idx % vector_size] += char / 255.0
    norm = max(sum(base), 1e-6)
    return [round(val / norm, 6) for val in base]


async def _openai_like_embedding(text: str) -> list[float]:
    if not EMBEDDING_BASE_URL:
        raise OrchestratorError("EMBEDDING_BASE_URL is not set for openai provider")
    url = EMBEDDING_BASE_URL.rstrip("/") + "/v1/embeddings"
    headers = {"content-type": "application/json"}
    if EMBEDDING_API_KEY:
        headers["authorization"] = f"Bearer {EMBEDDING_API_KEY}"
    payload = {"model": EMBEDDING_MODEL, "input": text}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise OrchestratorError(f"Embedding request failed: {resp.text}")
    data = resp.json()
    payloads = data.get("data") or []
    if not payloads:
        raise OrchestratorError("Embedding provider returned no data")
    return payloads[0]["embedding"]


async def _ollama_embedding(text: str) -> list[float]:
    url = OLLAMA_BASE_URL.rstrip("/") + "/api/embeddings"
    payload = {"model": EMBEDDING_MODEL, "prompt": text}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
    if resp.status_code != 200:
        raise OrchestratorError(f"Ollama embedding failed: {resp.text}")
    data = resp.json()
    vector = data.get("embedding")
    if vector is None and data.get("data"):
        vector = data["data"][0].get("embedding")
    if vector is None:
        raise OrchestratorError("Ollama response missing embedding field")
    return vector


async def embed_text(text: str) -> list[float]:
    provider = EMBEDDING_PROVIDER
    if provider in ("openai", "lmstudio", "openai-compatible"):
        try:
            return await _openai_like_embedding(text)
        except OrchestratorError:
            raise
        except Exception as exc:  # pragma: no cover - network failure
            raise OrchestratorError(str(exc)) from exc
    if provider == "ollama":
        try:
            return await _ollama_embedding(text)
        except OrchestratorError:
            raise
        except Exception as exc:  # pragma: no cover
            raise OrchestratorError(str(exc)) from exc
    # default fallback
    return _cheap_embedding(text, FALLBACK_EMBED_DIM)

app = FastAPI(title="memMCP orchestrator", version="0.1.0")
logger = logging.getLogger("memmcp.orchestrator")
telemetry_state: Dict[str, Any] = {
    "updatedAt": None,
    "queueDepth": 0,
    "batchSize": 0,
    "totals": {
        "enqueued": 0,
        "dropped": 0,
        "batches": 0,
        "flushedEvents": 0,
    },
}
trading_metrics_state: Dict[str, Any] = {
    "updatedAt": None,
    "openPositions": 0,
    "totalValueUsd": 0.0,
    "unrealizedPnl": 0.0,
    "realizedPnl": 0.0,
    "dailyPnl": 0.0,
    "positions": [],
}
trading_history = deque(maxlen=TRADING_HISTORY_LIMIT)
trading_history_lock = asyncio.Lock()
strategy_metrics_state: Dict[str, Any] = {
    "updatedAt": None,
    "strategies": [],
}
strategy_history = deque(maxlen=STRATEGY_HISTORY_LIMIT)
strategy_history_lock = asyncio.Lock()


def _apply_trading_snapshot(snapshot: Dict[str, Any]) -> None:
    timestamp = snapshot.get("timestamp")
    if isinstance(timestamp, datetime):
        trading_metrics_state["updatedAt"] = timestamp.isoformat()
    else:
        trading_metrics_state["updatedAt"] = timestamp
    trading_metrics_state["openPositions"] = snapshot.get("open_positions", 0)
    trading_metrics_state["totalValueUsd"] = snapshot.get("total_value_usd", 0.0)
    trading_metrics_state["unrealizedPnl"] = snapshot.get("unrealized_pnl", 0.0)
    trading_metrics_state["realizedPnl"] = snapshot.get("realized_pnl", 0.0)
    trading_metrics_state["dailyPnl"] = snapshot.get("daily_pnl", 0.0)
    trading_metrics_state["positions"] = snapshot.get("positions", [])


def _load_trading_history() -> None:
    if not TRADING_HISTORY_PATH.exists():
        return
    try:
        with TRADING_HISTORY_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                snapshot = json.loads(line)
                trading_history.append(snapshot)
        if trading_history:
            _apply_trading_snapshot(trading_history[-1])
    except Exception as exc:  # pragma: no cover - best-effort load
        logger.warning("Failed to load trading history: %s", exc)


async def _persist_trading_snapshot(snapshot: Dict[str, Any]) -> None:
    def _append(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)

    line = json.dumps(snapshot) + "\n"
    try:
        await asyncio.to_thread(_append, TRADING_HISTORY_PATH, line)
    except Exception as exc:  # pragma: no cover - disk full, etc.
        logger.warning("Failed to persist trading snapshot: %s", exc)


_load_trading_history()


def _apply_strategy_snapshot(snapshot: Dict[str, Any]) -> None:
    strategy_metrics_state["updatedAt"] = snapshot.get("timestamp")
    strategy_metrics_state["strategies"] = snapshot.get("strategies", [])


def _load_strategy_history() -> None:
    if not STRATEGY_HISTORY_PATH.exists():
        return
    try:
        with STRATEGY_HISTORY_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                snapshot = json.loads(line)
                strategy_history.append(snapshot)
        if strategy_history:
            _apply_strategy_snapshot(strategy_history[-1])
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load strategy history: %s", exc)


async def _persist_strategy_snapshot(snapshot: Dict[str, Any]) -> None:
    def _append(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)

    line = json.dumps(snapshot) + "\n"
    try:
        await asyncio.to_thread(_append, STRATEGY_HISTORY_PATH, line)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to persist strategy snapshot: %s", exc)


_load_strategy_history()


class MemoryWrite(BaseModel):
    projectName: str = Field(..., description="Project identifier")
    fileName: str = Field(..., description="File name inside the project")
    content: str = Field(..., description="Payload to store")


class TrajectoryIngest(BaseModel):
    project: str
    summary: str
    trajectory: dict[str, Any]


class TelemetryMetrics(BaseModel):
    timestamp: datetime
    queueDepth: int = Field(ge=0)
    batchSize: int = Field(ge=0)
    totals: Dict[str, int]


class TradingMetrics(BaseModel):
    timestamp: datetime
    open_positions: int
    total_value_usd: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    positions: list[dict[str, Any]]


class StrategyEntry(BaseModel):
    name: str
    capital: float
    win_rate: float | None = None
    daily_pnl: float | None = None
    notes: str | None = None
    memory_ref: str | None = None


class StrategyMetrics(BaseModel):
    timestamp: datetime
    strategies: list[StrategyEntry]


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


async def ensure_qdrant_collection(vector_size: int) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}")
    if resp.status_code == 200:
        body = resp.json()
        current_size = (
            body.get("result", {})
            .get("config", {})
            .get("params", {})
            .get("vectors", {})
            .get("size")
        )
        if current_size and current_size != vector_size:
            raise RuntimeError(
                "Qdrant collection dimension mismatch: "
                f"existing={current_size}, required={vector_size}. "
                "Drop the collection or adjust the embedding model."
            )
        return
    schema = {
        "vectors": {"size": vector_size, "distance": "Cosine"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        create = await client.put(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}", json=schema
        )
    if create.status_code not in (200, 202):
        raise RuntimeError(f"Failed to create Qdrant collection: {create.text}")


async def push_to_qdrant(project: str, file_name: str, content: str) -> None:
    vector = await embed_text(content)
    await ensure_qdrant_collection(len(vector))
    payload = {
        "points": [
            {
                "id": str(uuid.uuid4()),
                "vector": vector,
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


@app.post("/telemetry/metrics")
async def ingest_metrics(payload: TelemetryMetrics):
    telemetry_state["updatedAt"] = payload.timestamp.isoformat()
    telemetry_state["queueDepth"] = payload.queueDepth
    telemetry_state["batchSize"] = payload.batchSize
    totals = telemetry_state["totals"]
    totals.update({
        "enqueued": payload.totals.get("enqueued", totals.get("enqueued", 0)),
        "dropped": payload.totals.get("dropped", totals.get("dropped", 0)),
        "batches": payload.totals.get("batches", totals.get("batches", 0)),
        "flushedEvents": payload.totals.get("flushedEvents", totals.get("flushedEvents", 0)),
    })
    return {"ok": True}


@app.get("/telemetry/metrics")
async def get_metrics():
    return telemetry_state


@app.post("/telemetry/trading")
async def ingest_trading(payload: TradingMetrics):
    snapshot = payload.model_dump()
    snapshot["timestamp"] = payload.timestamp.isoformat()
    _apply_trading_snapshot(snapshot)
    async with trading_history_lock:
        trading_history.append(snapshot)
        history_size = len(trading_history)
    await _persist_trading_snapshot(snapshot)
    return {"ok": True, "historySize": history_size}


@app.get("/telemetry/trading")
async def get_trading_metrics():
    return trading_metrics_state


@app.get("/telemetry/trading/history")
async def get_trading_history(limit: int = 50):
    limit = max(1, min(limit, TRADING_HISTORY_LIMIT))
    async with trading_history_lock:
        items = list(trading_history)[-limit:]
    return {"history": items}


@app.post("/telemetry/strategies")
async def ingest_strategy_metrics(payload: StrategyMetrics):
    snapshot = payload.model_dump()
    snapshot["timestamp"] = payload.timestamp.isoformat()
    _apply_strategy_snapshot(snapshot)
    async with strategy_history_lock:
        strategy_history.append(snapshot)
        history_size = len(strategy_history)
    await _persist_strategy_snapshot(snapshot)
    return {"ok": True, "historySize": history_size}


@app.get("/telemetry/strategies")
async def get_strategy_metrics():
    return strategy_metrics_state


@app.get("/telemetry/strategies/history")
async def get_strategy_history(limit: int = 50):
    limit = max(1, min(limit, STRATEGY_HISTORY_LIMIT))
    async with strategy_history_lock:
        items = list(strategy_history)[-limit:]
    return {"history": items}
