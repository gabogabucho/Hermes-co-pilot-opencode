# Setup Guide

## Prerequisites

- [Hermes Agent](https://github.com/anomalyco/hermes) installed and configured
- [OpenCode](https://opencode.ai) installed
- Python 3.10+ (for the copilot server)

## Step 1: Start the Hermes Copilot Server

```bash
# From the hermes-agent directory
hermes copilot

# Or manually
cd src/server
pip install -r requirements.txt
python copilot_server.py --port 7878
```

You should see:
```
[hermes-copilot] Starting Hermes Copilot Server on localhost:7878
[hermes-copilot] Configure OpenCode with baseURL: http://localhost:7878/v1
```

## Step 2: Configure OpenCode

### Option A: With the plugin (recommended)

1. Install the plugin:
```bash
npm install -g @hermes-ai/opencode-copilot-plugin
```

2. Add to your project's `opencode.json`:
```json
{
  "plugin": ["@hermes-ai/opencode-copilot-plugin"]
}
```

The plugin will auto-detect your Hermes instance and register it.

### Option B: Manual setup (no plugin)

Create or edit `opencode.json` in your project root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "hermes": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Hermes Copilot",
      "options": {
        "baseURL": "http://localhost:7878/v1",
        "apiKey": "not-needed"
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

## Step 3: Select Hermes in OpenCode

1. Open OpenCode in your project
2. Run `/models` command
3. Select "Hermes Agent" from the list
4. Start coding!

## Configuration

### Server options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `7878` | Server port |
| `--host` | `localhost` | Bind address |
| `--log-level` | `info` | Logging level |

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_COPILOT_PORT` | `7878` | Server port |
| `HERMES_COPILOT_HOST` | `localhost` | Server host |
| `HERMES_HOME` | `~/.hermes` | Hermes config directory |

## Troubleshooting

### "Server not found at localhost:7878"

Make sure `hermes copilot` is running. Check with:
```bash
curl http://localhost:7878/health
```

### "Connection refused"

The server might be on a different port. Check the server logs and update your `opencode.json`.

### "Model not found"

Run `/models` in OpenCode to refresh the model list. Make sure your `opencode.json` has the `hermes-agent` model defined.

### Plugin not loading

Check OpenCode logs:
```bash
opencode --log-level debug
```

Make sure the plugin is installed globally or locally and the name matches in your config.
