import type { Plugin } from "@opencode-ai/plugin"

const HERMES_GATEWAY_PORT = Number(process.env.API_SERVER_PORT || 8642)
const HERMES_GATEWAY_HOST = process.env.API_SERVER_HOST || "127.0.0.1"
const HERMES_GATEWAY_URL = `http://${HERMES_GATEWAY_HOST}:${HERMES_GATEWAY_PORT}`

/**
 * Check if the Hermes gateway API is running.
 */
async function detectGateway(): Promise<boolean> {
  try {
    const res = await fetch(`${HERMES_GATEWAY_URL}/health`, {
      signal: AbortSignal.timeout(2000),
    })
    const data = await res.json()
    return data.status === "ok"
  } catch {
    return false
  }
}

/**
 * Hermes Copilot Plugin for OpenCode.
 *
 * Auto-detects the Hermes gateway API and simplifies connection.
 * When the gateway is running with API_SERVER_ENABLED=true,
 * OpenCode gets access to your Hermes agent's memory, skills, and tools.
 */
export const HermesCopilotPlugin: Plugin = async ({ project, client, $ }) => {
  const gatewayAvailable = await detectGateway()

  if (!gatewayAvailable) {
    console.log(
      `[Hermes Copilot] Gateway not found at ${HERMES_GATEWAY_URL}.\n` +
        `  Enable it: echo "API_SERVER_ENABLED=true" >> ~/.hermes/.env\n` +
        `  Then: hermes gateway restart`
    )
    return {}
  }

  console.log(`[Hermes Copilot] Gateway detected at ${HERMES_GATEWAY_URL}`)

  return {
    /**
     * Inject project context when using hermes models.
     * Gives Hermes awareness of git branch and working directory.
     */
    "chat.params": async ({ model, provider, message }, params) => {
      if (!model?.includes("hermes")) return

      try {
        const branch = await $`git branch --show-current`
          .text()
          .catch(() => "unknown")

        params.options = params.options || {}
        params.options.hermes_context = [
          `[Project: ${project.id}]`,
          `[Branch: ${branch.trim()}]`,
          `[Dir: ${project.worktree || process.cwd()}]`,
        ].join(" ")
      } catch {
        // Non-critical — continue without context
      }
    },

    event: async ({ event }) => {
      if (event.type === "session.created") {
        console.log("[Hermes Copilot] Session started — using Hermes agent")
      }
    },
  }
}

export default HermesCopilotPlugin
