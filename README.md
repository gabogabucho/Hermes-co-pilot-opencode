# Hermes Copilot for OpenCode

Use your [Hermes Agent](https://github.com/NousResearch/hermes-agent) as the AI provider in [OpenCode](https://opencode.ai). Your agent's memory, skills, and context — in every coding session.

## What is this?

When you use Claude or GPT in OpenCode, you get a generic model. With Hermes Copilot, OpenCode sends every request through **your Hermes instance** — the one that knows your projects, your conventions, your memory. Not just text completion, but a reasoning agent with tools.

## How it works

```
OpenCode (your editor/IDE)
    ↓ HTTP (OpenAI-compatible API)
Hermes Gateway (localhost:8642)
    ↓ Full agent pipeline
Hermes Agent (memory + skills + tools + reasoning)
    ↓ LLM API
Your chosen model (Claude, DeepSeek, GPT-4, etc.)
```

**No proxy needed.** Hermes gateway already exposes `/v1/chat/completions` — OpenCode connects directly.

## Quick Start

### 1. Enable the API server in Hermes

Add to `~/.hermes/.env`:

```bash
echo "API_SERVER_ENABLED=true" >> ~/.hermes/.env
```

### 2. Start (or restart) the gateway

```bash
hermes gateway restart
```

Verify it's running:

```bash
curl http://127.0.0.1:8642/health
# → {"status": "ok"}

curl http://127.0.0.1:8642/v1/models
# → {"object": "list", "data": [{"id": "hermes-agent", ...}]}
```

### 3. Configure OpenCode

Create or edit `opencode.json` in your project root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "hermes": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Hermes Agent",
      "options": {
        "baseURL": "http://127.0.0.1:8642/v1"
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

### 4. Select Hermes in OpenCode

Run `/models` in OpenCode, select **Hermes Agent**. Done.

## Remote / Non-local setups

If OpenCode runs on a different machine than Hermes (e.g., Hermes on a VPS, OpenCode on your laptop), you need to expose the gateway port.

### Option A: SSH tunnel (recommended, secure)

```bash
# From your local machine, tunnel to the remote gateway
ssh -L 8642:127.0.0.1:8642 user@your-vps-ip
```

Then point OpenCode at `http://127.0.0.1:8642/v1` — the tunnel handles the rest.

### Option B: Tailscale (zero-config, encrypted)

If both machines are on the same Tailscale network:

```bash
# On the Hermes machine, check its Tailscale IP
tailscale ip -4
# → 100.x.x.x
```

Point OpenCode at `http://100.x.x.x:8642/v1`.

### Option C: Expose on all interfaces (less secure)

Edit `~/.hermes/.env`:

```bash
# Bind the API server to all interfaces (not just localhost)
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
```

Then use `http://your-vps-ip:8642/v1` in OpenCode.

**⚠️ Warning:** This exposes the API to the internet. Use only behind a firewall, VPN, or with auth middleware.

### Option D: Reverse proxy with auth (production)

Use nginx/caddy with basic auth or token-based auth in front of port 8642. See the [gateway docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) for reference.

## Optional: OpenCode Plugin

The included plugin (`@hermes-ai/opencode-copilot-plugin`) auto-detects your Hermes gateway and simplifies setup. It:

1. Checks if the gateway is running on `localhost:8642`
2. Injects project context (git branch, directory) into requests
3. Shows Hermes status feedback

### Install

```bash
npm install -g @hermes-ai/opencode-copilot-plugin
```

Add to `opencode.json`:

```json
{
  "plugin": ["@hermes-ai/opencode-copilot-plugin"]
}
```

**You don't need the plugin for basic functionality** — just the provider config is enough. The plugin is UX polish.

## What you get

When OpenCode sends a request through Hermes:

- **Memory**: Hermes remembers your architecture decisions, coding style, past debugging sessions
- **Skills**: Hermes can use installed skills for code review, testing patterns, deployment
- **Tools**: Hermes can search the web, read files, execute code — all before responding
- **Model routing**: Hermes picks the best model for the task (configurable)
- **Session continuity**: Hermes remembers context across coding sessions

## Configuration Reference

### Hermes side (`~/.hermes/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SERVER_ENABLED` | `false` | Enable the HTTP API server |
| `API_SERVER_HOST` | `127.0.0.1` | Bind address for the API |
| `API_SERVER_PORT` | `8642` | Port for the API server |

### OpenCode side (`opencode.json`)

See `opencode.example.json` in this repo for a complete example.

## Troubleshooting

### `curl: (7) Failed to connect to 127.0.0.1 port 8642`

The gateway isn't running or the API isn't enabled. Check:

```bash
# Is the gateway running?
ps aux | grep hermes

# Is it listening on 8642?
ss -tlnp | grep 8642

# Is the env var set?
cat ~/.hermes/.env | grep API_SERVER
```

### `{"status": "ok"}` but OpenCode can't connect

Make sure you're using `127.0.0.1` (not `localhost`) in the baseURL. Some systems resolve `localhost` to IPv6 which may not work.

### Model not showing in OpenCode

Run `/models` in OpenCode to refresh. Make sure the `hermes-agent` key exists in your `opencode.json` provider config.

### Slow responses

Hermes is an agent, not a raw LLM. It may read files, search memory, or use tools before responding. First requests are slower (cold start). Subsequent requests benefit from prompt caching.

## Project Structure

```
Hermes-co-pilot-opencode/
├── README.md                    # This file
├── opencode.example.json        # Copy-paste config for OpenCode
├── docs/
│   └── SETUP.md                 # Detailed setup guide
├── src/
│   ├── server/
│   │   ├── copilot_server.py    # Optional bridge (for non-standard setups)
│   │   └── requirements.txt
│   └── plugin/
│       ├── src/index.ts         # OpenCode auto-discovery plugin
│       ├── package.json
│       └── tsconfig.json
```

## License

MIT
