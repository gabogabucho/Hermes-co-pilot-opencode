"""
Hermes Copilot Bridge — Optional OpenAI-compatible proxy for non-standard setups.

This bridge is NOT required for normal use. OpenCode can connect directly to
the Hermes gateway on port 8642. Use this bridge only if you need:

  - Port translation (e.g., gateway on 8642, bridge on 7878)
  - Extra context injection (project files, git info)
  - Multiple Hermes instances behind one endpoint
  - CORS handling for web-based IDEs

Usage:
    python copilot_server.py [--port 7878] [--upstream http://127.0.0.1:8642]

Then configure OpenCode to use:
    baseURL: http://localhost:7878/v1

For direct connection (recommended), skip this and point OpenCode at:
    baseURL: http://127.0.0.1:8642/v1
"""

import json
import os
import argparse
import logging
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import uvicorn

logger = logging.getLogger("hermes-copilot-bridge")

# Defaults
DEFAULT_UPSTREAM = os.environ.get("HERMES_GATEWAY_URL", "http://127.0.0.1:8642")
DEFAULT_PORT = int(os.environ.get("HERMES_COPILOT_PORT", "7878"))
DEFAULT_HOST = os.environ.get("HERMES_COPILOT_HOST", "localhost")


app = FastAPI(
    title="Hermes Copilot Bridge",
    description="Optional bridge for connecting OpenCode to Hermes gateway",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared HTTP client for upstream requests
upstream_client: httpx.AsyncClient = None  # type: ignore
upstream_url: str = DEFAULT_UPSTREAM


@app.on_event("startup")
async def startup():
    global upstream_client
    upstream_client = httpx.AsyncClient(
        base_url=upstream_url,
        timeout=httpx.Timeout(300.0, connect=10.0),
    )
    logger.info(f"Upstream: {upstream_url}")


@app.on_event("shutdown")
async def shutdown():
    await upstream_client.aclose()


@app.get("/")
async def root():
    return {
        "name": "hermes-copilot-bridge",
        "upstream": upstream_url,
        "endpoints": ["/v1/models", "/v1/chat/completions", "/health"],
    }


@app.get("/health")
async def health():
    """Check both bridge and upstream health."""
    try:
        resp = await upstream_client.get("/health")
        upstream_ok = resp.status_code == 200
    except Exception:
        upstream_ok = False

    return {
        "status": "ok" if upstream_ok else "degraded",
        "bridge": "ok",
        "upstream": upstream_url,
        "upstream_ok": upstream_ok,
    }


@app.get("/v1/models")
async def list_models():
    """Proxy model listing from upstream gateway."""
    try:
        resp = await upstream_client.get("/v1/models")
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Proxy chat completions to upstream gateway.

    Supports both streaming and non-streaming. Passes through to hermes
    gateway without modification — hermes handles all agent logic.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    stream = body.get("stream", True)

    try:
        if stream:
            return StreamingResponse(
                stream_upstream(body),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            resp = await upstream_client.post(
                "/v1/chat/completions",
                json=body,
            )
            return JSONResponse(resp.json())
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot connect to Hermes gateway at {upstream_url}. "
            f"Is it running? Start with: hermes gateway restart",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")


async def stream_upstream(body: dict) -> AsyncIterator[str]:
    """Stream SSE from upstream gateway to client."""
    async with upstream_client.stream(
        "POST", "/v1/chat/completions", json=body
    ) as resp:
        async for chunk in resp.aiter_text():
            yield chunk


def main():
    global upstream_url

    parser = argparse.ArgumentParser(
        description="Hermes Copilot Bridge — optional proxy for OpenCode"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Bridge port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"Bridge bind address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--upstream", default=DEFAULT_UPSTREAM,
        help=f"Hermes gateway URL (default: {DEFAULT_UPSTREAM})",
    )
    parser.add_argument(
        "--log-level", default="info",
        help="Log level (default: info)",
    )
    args = parser.parse_args()

    upstream_url = args.upstream

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger.info(f"Hermes Copilot Bridge on {args.host}:{args.port}")
    logger.info(f"Upstream gateway: {upstream_url}")
    logger.info(f"OpenCode baseURL: http://{args.host}:{args.port}/v1")
    logger.info("")
    logger.info("Tip: If gateway is on localhost:8642, you can connect")
    logger.info("     OpenCode directly without this bridge.")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
