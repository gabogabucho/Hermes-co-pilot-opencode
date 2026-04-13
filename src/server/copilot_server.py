"""
Hermes Copilot Server — OpenAI-compatible API proxy for OpenCode.

Receives chat completion requests from OpenCode and routes them through
Hermes Agent, injecting memory, skills, and project context.

Usage:
    python copilot_server.py [--port 7878] [--host localhost]

Then configure OpenCode to use:
    baseURL: http://localhost:7878/v1
"""

import json
import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

# ---------------------------------------------------------------------------
# Hermes integration
# ---------------------------------------------------------------------------

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
logger = logging.getLogger("hermes-copilot")


def get_hermes_config() -> dict:
    """Load Hermes config.yaml."""
    config_path = HERMES_HOME / "config.yaml"
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_available_models() -> list[dict]:
    """Return models available through this proxy."""
    return [
        {
            "id": "hermes-agent",
            "object": "model",
            "created": 0,
            "owned_by": "hermes",
            "name": "Hermes Agent",
            "description": "Hermes reasoning agent with memory, skills, and tools",
        },
        {
            "id": "hermes-fast",
            "object": "model",
            "created": 0,
            "owned_by": "hermes",
            "name": "Hermes Fast",
            "description": "Hermes lightweight mode — no tools, fast responses",
        },
    ]


# ---------------------------------------------------------------------------
# Request processing
# ---------------------------------------------------------------------------

def extract_project_context(messages: list[dict]) -> dict:
    """Extract project context from OpenCode messages.

    OpenCode sends system prompts and user messages that contain
    project info. We extract what we can for Hermes context injection.
    """
    context = {
        "source": "opencode",
        "project_files": [],
        "current_file": None,
    }

    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            # OpenCode often includes file paths in system prompts
            if "Current file:" in content or "Working directory:" in content:
                context["system_info"] = content[:2000]

    return context


def build_hermes_prompt(messages: list[dict], project_context: dict) -> str:
    """Build a Hermes-compatible prompt from OpenCode messages.

    Since Hermes is an agent (not a raw LLM), we need to format the
    conversation into a single task prompt that Hermes can reason about.
    """
    parts = []

    # Add project context hint
    if project_context.get("system_info"):
        parts.append(f"[OpenCode Context]\n{project_context['system_info']}\n")

    # Add conversation
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            continue  # Already handled above
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Streaming response generator
# ---------------------------------------------------------------------------

async def stream_hermes_response(
    prompt: str,
    model: str,
    request_id: str,
) -> AsyncIterator[str]:
    """Stream a response from Hermes as OpenAI-compatible SSE.

    Yields Server-Sent Event strings in OpenAI chat.completion.chunk format.
    """
    # TODO: Replace with actual Hermes agent call
    # This is the integration point where we call hermes_agent.chat()
    # For now, emit a placeholder that proves the plumbing works.

    placeholder = (
        f"[Hermes Copilot] Model: {model} | "
        f"Received {len(prompt)} chars. "
        f"Integration with Hermes Agent pending."
    )

    # Stream token by token
    for i, char in enumerate(placeholder):
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": char},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.01)

    # Final chunk
    final = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final)}\n\n"
    yield "data: [DONE]\n\n"


async def call_hermes_agent(
    prompt: str,
    model: str,
) -> str:
    """Call Hermes Agent synchronously (non-streaming fallback).

    TODO: Replace with actual hermes integration.
    """
    return (
        f"[Hermes Copilot] Model: {model} | "
        f"Received {len(prompt)} chars. "
        f"Integration with Hermes Agent pending."
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Hermes Copilot Server",
    description="OpenAI-compatible proxy for Hermes Agent — use Hermes as your coding provider in OpenCode",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "hermes-copilot",
        "version": "0.1.0",
        "description": "Hermes Agent — OpenAI-compatible API for OpenCode",
        "endpoints": [
            "/v1/models",
            "/v1/chat/completions",
            "/health",
        ],
    }


@app.get("/health")
async def health():
    config = get_hermes_config()
    return {
        "status": "ok",
        "hermes_home": str(HERMES_HOME),
        "config_loaded": bool(config),
    }


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible model listing."""
    return {
        "object": "list",
        "data": get_available_models(),
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint.

    This is what OpenCode calls. We receive the messages, inject
    Hermes context, and return the response (streamed or not).
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    messages = body.get("messages", [])
    model = body.get("model", "hermes-agent")
    stream = body.get("stream", True)

    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Extract project context from OpenCode messages
    project_context = extract_project_context(messages)

    # Build Hermes prompt
    prompt = build_hermes_prompt(messages, project_context)

    request_id = f"hermes-copilot-{os.urandom(8).hex()}"

    if stream:
        return StreamingResponse(
            stream_hermes_response(prompt, model, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-Id": request_id,
            },
        )
    else:
        response_text = await call_hermes_agent(prompt, model)
        return JSONResponse(
            {
                "id": request_id,
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response_text.split()),
                    "total_tokens": len(prompt.split()) + len(response_text.split()),
                },
            }
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Hermes Copilot Server")
    parser.add_argument("--port", type=int, default=7878)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger.info(f"Starting Hermes Copilot Server on {args.host}:{args.port}")
    logger.info(f"Hermes home: {HERMES_HOME}")
    logger.info(f"Configure OpenCode with baseURL: http://{args.host}:{args.port}/v1")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
