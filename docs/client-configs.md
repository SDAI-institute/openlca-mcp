# openLCA MCP Client Configuration

The current v0.4.1 FastMCP entry point supports two primary connection modes:

| Mode | Endpoint/process | Use |
|---|---|---|
| **stdio** | client launches `python -m src` | Local desktop/developer clients |
| **Streamable HTTP** | `https://host/mcp` | Remote/web/sandboxed agent clients, services, and workflows |

The examples below assume the repository is cloned and installed, and openLCA Desktop is running with its IPC server enabled.

## Local installation

```bash
git clone https://github.com/SDAI-institute/openlca-mcp.git
cd openlca-mcp
pip install -e .
```

Test the server directly:

```bash
python -m src
```

## stdio configuration pattern

Clients that can launch local MCP processes use the same basic configuration:

```json
{
  "command": "python",
  "args": ["-m", "src"],
  "cwd": "/absolute/path/to/openlca-mcp",
  "env": {
    "OPENLCA_HOST": "localhost",
    "OPENLCA_PORT": "8080"
  }
}
```

### Claude Desktop / Cursor-style configuration

```json
{
  "mcpServers": {
    "openlca": {
      "command": "python",
      "args": ["-m", "src"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

### VS Code-style configuration

```json
{
  "servers": {
    "openlca": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "src"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

### OpenAI Codex CLI-style configuration

```toml
[mcp_servers.openlca]
command = "python"
args = ["-m", "src"]
cwd = "/absolute/path/to/openlca-mcp"

[mcp_servers.openlca.env]
OPENLCA_PORT = "8080"
```

## Streamable HTTP

Start the server in HTTP mode:

```bash
TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 python -m src
```

The MCP endpoint is:

```text
http://localhost:8000/mcp
```

For a remote deployment, terminate TLS in front of the server and expose only the protected `/mcp` endpoint.

## Remote and web-hosted MCP clients

Register the HTTPS MCP endpoint supplied by your deployment, for example:

```text
https://mcp.example.com/mcp
```

The current source registers 28 tools. If a remote client connects but exposes no tool surface, verify the endpoint is using MCP streamable HTTP correctly and that any reverse proxy is not buffering the stream.

When authentication is enabled, prefer `Authorization: Bearer <key>` in clients that support headers. The optional SDAI gateway can also accept the configured query-token form for clients that cannot set custom headers; treat such URLs as secrets because query strings may be logged.

## n8n and workflow services

When n8n can reach the MCP server over HTTP, use the `/mcp` URL rather than spawning a separate process inside each workflow.

Examples:

```text
http://openlca-mcp:8000/mcp           # same container network
http://host.docker.internal:8000/mcp # MCP server on Docker host
https://mcp.example.com/mcp          # protected remote endpoint
```

See [n8n Integration](n8n-integration.md) for workflow design.

## Connection profiles

One server can target several openLCA instances. Configure profiles with `OPENLCA_CONNECTIONS` or `OPENLCA_CONNECTIONS_FILE`, then pass the optional `connection` argument on tool calls. Authentication can restrict callers to specific profiles.

## Read-only deployments

Use `OPENLCA_READ_ONLY=true` for documentation demos, inspection workflows, and other contexts that should not modify the openLCA database. Search and calculation tools remain available; create/write operations return `WRITE_BLOCKED`.

## Troubleshooting

| Symptom | Check |
|---|---|
| Local server starts but client shows no tools | `cwd`, Python environment, and `python -m src` |
| MCP endpoint cannot be reached | HTTP transport, port binding, firewall/reverse proxy |
| MCP works but openLCA calls fail | openLCA Desktop, active database, IPC server, host/port |
| Remote client connects but no tools appear | proxy buffering/streaming behavior and correct `/mcp` URL |
| Write calls fail with `WRITE_BLOCKED` | connection profile or `OPENLCA_READ_ONLY` setting |
| Wrong database is queried | confirm which database is open in the target openLCA instance |

## Security boundary

Do not expose an unauthenticated write-enabled MCP endpoint to the public internet. Network authentication, connection-profile authorization, read-only defaults, and database backups are operational controls; they do not replace LCA model review.