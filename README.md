# Hermes Copilot for OpenCode

Connect your [Hermes Agent](https://github.com/anomalyco/hermes) instance as an AI provider in [OpenCode](https://opencode.ai). Write code with your own personal coding agent that knows your projects, your conventions, and your memory.

## Why?

When you use Claude or GPT in OpenCode, you get a generic model that starts from zero every time. With Hermes Copilot, you get:

- **Your memory** — Hermes remembers your architecture decisions, coding style, and project conventions
- **Your skills** — Hermes can use installed skills (code review, testing patterns, deployment)
- **Your context** — Hermes can read your project files, search docs, execute code to verify before responding
- **Your models** — Hermes picks the best model for each task (DeepSeek for boilerplate, Claude for architecture, etc.)

## Architecture

```
OpenCode (your editor)
    ↓ HTTP (OpenAI-compatible API)
Hermes Copilot Server (localhost:7878)
    ↓ Internal
Hermes Agent (reasoning + tools + memory)
    ↓ LLM API
Your chosen model (Claude, DeepSeek, GPT-4, etc.)
```

## Quick Start

### 1. Start the Hermes Copilot server

```bash
hermes copilot
# or
hermes copilot --port 7878
```

### 2. Configure OpenCode

Add to your `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "hermes": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Hermes Copilot",
      "options": {
        "baseURL": "http://localhost:7878/v1"
      },
      "models": {
        "hermes-agent": {
          "name": "Hermes Agent",
          "limit": {
            "context": 200000,
            "output": 65536
          }
        }
      }
    }
  }
}
```

### 3. Select Hermes in OpenCode

Run `/models` in OpenCode and select `hermes-agent`. That's it.

## Installation

### Option A: Auto-install (recommended)

```bash
npm install -g @hermes-ai/opencode-copilot-plugin
```

Then add to your `opencode.json`:

```json
{
  "plugin": ["@hermes-ai/opencode-copilot-plugin"]
}
```

The plugin will auto-detect your Hermes instance and configure the provider.

### Option B: Manual setup

Just use the config from Quick Start step 2. No plugin needed — it works with the standard `@ai-sdk/openai-compatible` provider.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_COPILOT_PORT` | `7878` | Port for the copilot server |
| `HERMES_COPILOT_HOST` | `localhost` | Host to bind to |
| `HERMES_HOME` | `~/.hermes` | Hermes home directory |
| `HERMES_COPILOT_MODEL` | auto | Force a specific model |

### Advanced: Custom model routing

Hermes can route to different models based on the task:

```json
{
  "provider": {
    "hermes-claude": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:7878/v1" },
      "models": {
        "hermes-claude": { "name": "Hermes (Claude)" }
      }
    },
    "hermes-deepseek": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:7878/v1" },
      "models": {
        "hermes-deepseek": { "name": "Hermes (DeepSeek)" }
      }
    }
  }
}
```

Hermes automatically selects the best model, but you can force one by choosing the specific model in OpenCode.

## How It Works

### The Server (`hermes copilot`)

The copilot server is a lightweight HTTP server that:

1. Receives OpenAI-compatible chat completion requests from OpenCode
2. Injects Hermes context (memory, project files, skills)
3. Forwards to the appropriate LLM via Hermes's model routing
4. Streams the response back to OpenCode

### The Plugin (optional)

The `@hermes-ai/opencode-copilot-plugin` plugin:

1. Auto-discovers the Hermes copilot server on localhost
2. Registers "Hermes" as a provider in OpenCode's UI
3. Injects project context headers (current file, git branch, etc.)
4. Shows Hermes status in the OpenCode sidebar

## Development

```bash
git clone https://github.com/gabogabucho/Hermes-co-pilot-opencode.git
cd Hermes-co-pilot-opencode

# Server (Python - lives in Hermes)
cd src/server
pip install -r requirements.txt
python copilot_server.py

# Plugin (TypeScript - lives in OpenCode)
cd src/plugin
bun install
bun run build
```

## License

MIT
