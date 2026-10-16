# Agent Client Protocol (ACP)

OpenCode can act as an ACP agent so editors/IDEs (e.g. Zed) can drive it over
JSON-RPC via stdio. No separate MCP server is required.

## Run

```sh
opencode acp
# or with a working directory:
opencode acp --cwd /path/to/project
```

One process can serve many ACP sessions. It exits when the client closes stdin.

## Editor configuration (example: Zed)

```json
{
  "agent_servers": {
    "OpenCode": {
      "command": "opencode",
      "args": ["acp"]
    }
  }
}
```

If the editor cannot find `opencode`, set `command` to the absolute path from
`which opencode`.

## MCP servers over ACP

ACP clients can pass stdio/HTTP MCP servers on `session/new`, `session/load`,
`session/resume`, and `session/fork`. OpenCode adds them for the life of the
`opencode acp` process. HTTP headers are passed through; OAuth is not used for
these servers.

## Notes

- `opencode acp` starts a private OpenCode server; it does not connect to the
  shared background service and opens no network port for ACP.
- Built-in tools, custom tools, slash commands, MCP servers from config, project
  rules from `AGENTS.md`, and the agents/permissions system all work via ACP.
- See OpenCode docs: https://opencode.ai/v2/docs/cli/acp/
