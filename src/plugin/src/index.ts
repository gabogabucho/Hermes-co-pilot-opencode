import type { Plugin } from "@opencode-ai/plugin"

const HERMES_COPILOT_PORT = Number(process.env.HERMES_COPILOT_PORT || 7878)
const HERMES_COPILOT_HOST = process.env.HERMES_COPILOT_HOST || "localhost"
const HERMES_COPILOT_URL = `http://${HERMES_COPILOT_HOST}:${HERMES_COPILOT_PORT}`

/**
 * Check if the Hermes Copilot server is running.
 */
async function detectHermesServer(): Promise<boolean> {
  try {
    const res = await fetch(`${HERMES_COPILOT_URL}/health`, {
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
 * Auto-detects the Hermes Copilot server and registers it as a provider.
 * Users with Hermes running get a "Hermes Copilot" option in their model list.
 */
export const HermesCopilotPlugin: Plugin = async ({ project, client, $ }) => {
  // Check if Hermes is running on startup
  const hermesAvailable = await detectHermesServer()

  if (!hermesAvailable) {
    console.log(
      `[Hermes Copilot] Server not found at ${HERMES_COPILOT_URL}. ` +
        `Start it with: hermes copilot`
    )
    return {}
  }

  console.log(`[Hermes Copilot] Connected to ${HERMES_COPILOT_URL}`)

  return {
    /**
     * Inject project context into chat messages.
     * This gives Hermes awareness of what you're working on.
     */
    "chat.params": async ({ model, provider, message }, params) => {
      // Only inject context when using hermes provider
      if (!model?.includes("hermes")) return

      try {
        // Get current git branch
        const branch = await $`git branch --show-current`.text().catch(() => "unknown")

        // Get current file from message context if available
        const contextParts = [
          `[Project: ${project.id}]`,
          `[Branch: ${branch.trim()}]`,
          `[Directory: ${project.worktree || process.cwd()}]`,
        ]

        // Add project context as a system hint
        // This gets passed as extra headers to our server
        params.options = params.options || {}
        params.options.hermes_context = contextParts.join(" ")
      } catch (err) {
        // Non-critical — continue without context
      }
    },

    /**
     * Log events for debugging.
     */
    event: async ({ event }) => {
      if (event.type === "session.created") {
        console.log("[Hermes Copilot] New session started")
      }
    },
  }
}

// Default export for OpenCode plugin loading
export default HermesCopilotPlugin
