# Detailed Setup Guide

## Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed and configured
- [OpenCode](https://opencode.ai) installed
- Your Hermes gateway running (`hermes gateway run`)

## Step 1: Enable the Hermes API Server

The gateway can expose an OpenAI-compatible HTTP API. It's opt-in.

```bash
# Add to your Hermes .env
echo "API_SERVER_ENABLED=true" >> ~/.hermes/.env
```

### Restart the gateway

```bash
# If running as a process
hermes gateway restart

# If running as systemd service
sudo systemctl restart hermes-gateway
```

### Verify it's running

```bash
# Health check
curl http://127.0.0.1:8642/health
# Expected: {"status": "ok"}

# List available models
curl http://127.0.0.1:8642/v1/models
# Expected: {"object": "list", "data": [{"id": "hermes-agent", ...}]}

# Test a completion
curl http://127.0.0.1:8642/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "hermes-agent", "messages": [{"role": "user", "content": "say hi"}], "stream": false}'
```

## Step 2: Configure OpenCode

### Option A: Direct connection (recommended)

No plugin needed. Edit `opencode.json` in your project:

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
          "limit": { "context": 200000, "output": 65536 }
        }
      }
    }
  }
}
```

### Option B: With the auto-discovery plugin

```bash
npm install -g @hermes-ai/opencode-copilot-plugin
```

Add to `opencode.json`:

```json
{
  "plugin": ["@hermes-ai/opencode-copilot-plugin"]
}
```

The plugin detects if the gateway is running and registers the provider automatically.

## Step 3: Select Hermes in OpenCode

1. Open OpenCode in your project
2. Run `/models`
3. Select **Hermes Agent**
4. Start coding

## Exposing the Gateway for Remote Access

If OpenCode runs on a different machine than Hermes:

### SSH tunnel (easiest, most secure)

```bash
# From your local machine
ssh -L 8642:127.0.0.1:8642 user@remote-host
```

Then use `http://127.0.0.1:8642/v1` in OpenCode locally.

### Tailscale (zero-config mesh VPN)

```bash
# On the Hermes machine
tailscale ip -4
# → 100.64.0.1

# On the OpenCode machine, use http://100.64.0.1:8642/v1
```

### Bind to all interfaces

Edit `~/.hermes/.env`:

```bash
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
```

Restart gateway. Use `http://your-ip:8642/v1`.

**⚠️ Only do this on trusted networks.** The API has no built-in auth.

### Nginx reverse proxy with auth (production)

```nginx
server {
    listen 443 ssl;
    server_name hermes.yourdomain.com;

    location / {
        auth_basic "Hermes";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://127.0.0.1:8642;
        proxy_set_header Host $host;
        proxy_buffering off;  # Important for SSE streaming
    }
}
```

## Using the Optional Bridge

If you need port translation or extra features, use the included bridge:

```bash
cd src/server
pip install -r requirements.txt
python copilot_server.py --port 7878 --upstream http://127.0.0.1:8642
```

Then point OpenCode at `http://localhost:7878/v1`.

## Environment Variables Reference

### Hermes side (`~/.hermes/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SERVER_ENABLED` | `false` | Enable HTTP API on the gateway |
| `API_SERVER_HOST` | `127.0.0.1` | Bind address |
| `API_SERVER_PORT` | `8642` | Port number |

### Bridge side

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_GATEWAY_URL` | `http://127.0.0.1:8642` | Upstream gateway URL |
| `HERMES_COPILOT_PORT` | `7878` | Bridge port |
| `HERMES_COPILOT_HOST` | `localhost` | Bridge bind address |

## Troubleshooting

### Gateway not listening on 8642

```bash
# Check if process is running
ps aux | grep hermes

# Check what ports it has open
ss -tlnp | grep $(pgrep -f "hermes.*gateway")

# Verify env var is set
cat ~/.hermes/.env | grep API_SERVER
```

### Use `127.0.0.1`, not `localhost`

Some systems resolve `localhost` to `::1` (IPv6). Use `127.0.0.1` explicitly.

### OpenCode says "model not found"

Run `/models` in OpenCode to refresh. Verify the model key in `opencode.json`:

```bash
curl http://127.0.0.1:8642/v1/models | python -m json.tool
```

The model ID must match what's in your config.

### Slow first response

Hermes loads context on first request (memory, skills, config). Subsequent requests are faster thanks to prompt caching.
