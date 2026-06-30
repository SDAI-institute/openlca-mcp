# Client Configuration

Copy-paste configs for connecting the openLCA MCP server to popular AI clients.

Three connection modes:

| Mode | How it works | When to use |
|------|-------------|-------------|
| **stdio** | Client spawns the server process directly over stdin/stdout | Claude Desktop, Cursor, VS Code — running locally |
| **Streamable HTTP** | Client connects to a single MCP endpoint such as `/mcp` | ChatGPT apps, OpenAI developer mode, modern remote MCP clients |
| **SSE** | Client connects to the legacy `/sse` + `/messages/` transport | Older remote clients and backwards compatibility |

---

## Prerequisites

### For stdio mode — clone and install once

```bash
git clone https://github.com/SDAI-institute/openlca-mcp.git
cd openlca-mcp
pip install -r requirements.txt
```

Note the **absolute path** to the cloned directory — you'll need it in every config below.

- macOS/Linux: `/Users/you/openlca-mcp`
- Windows: `C:\Users\you\openlca-mcp`

### For remote HTTP mode — server must be running first

```bash
# local Docker
docker compose up -d          # → http://localhost:8000/mcp and /sse

# or direct
TRANSPORT=http python -m src.server
```

See [DOCKER.md](../DOCKER.md) for full Docker and production setup.

### openLCA must be running with IPC server enabled

openLCA → Tools → Developer Tools → IPC Server → Start (default port 8080)

---

## Claude Desktop

**Config file:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### stdio (local — recommended)

```json
{
  "mcpServers": {
    "openlca": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

### Remote MCP (preferred for modern clients)

```json
{
  "mcpServers": {
    "openlca": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### SSE (legacy)

```json
{
  "mcpServers": {
    "openlca": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

```json
{
  "mcpServers": {
    "openlca": {
      "url": "https://mcp.yourdomain.com/sse"
    }
  }
}
```

Restart Claude Desktop after saving.

### uvx one-liner (no clone needed, once published to PyPI)

```json
{
  "mcpServers": {
    "openlca": {
      "command": "uvx",
      "args": ["openlca-mcp-server"],
      "env": { "OPENLCA_PORT": "8080" }
    }
  }
}
```

Or directly from GitHub:

```json
{
  "mcpServers": {
    "openlca": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/SDAI-institute/openlca-mcp",
        "openlca-mcp"
      ],
      "env": { "OPENLCA_PORT": "8080" }
    }
  }
}
```

---

## Cursor

**Config file:**
- Global: `~/.cursor/mcp.json`
- Project-scoped: `.cursor/mcp.json` in the project root

### stdio

```json
{
  "mcpServers": {
    "openlca": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

### SSE

```json
{
  "mcpServers": {
    "openlca": {
      "url": "http://localhost:8000/sse",
      "type": "sse"
    }
  }
}
```

---

## VS Code (GitHub Copilot agent mode)

VS Code 1.99+ with GitHub Copilot supports MCP servers in agent mode.

**Config file:** `.vscode/mcp.json` (project) or user `settings.json`

### stdio

```json
{
  "servers": {
    "openlca": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

Windows path example:
```json
{
  "servers": {
    "openlca": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\Users\\you\\openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

### SSE

```json
{
  "servers": {
    "openlca": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## OpenAI Codex CLI

**Config file:** `~/.codex/config.toml`

### stdio

```toml
[mcp_servers.openlca]
command = "python"
args   = ["-m", "src.server"]
cwd    = "/absolute/path/to/openlca-mcp"

[mcp_servers.openlca.env]
OPENLCA_PORT = "8080"
```

### Remote MCP (preferred)

```toml
[mcp_servers.openlca]
url = "http://localhost:8000/mcp"
```

### SSE (legacy)

```toml
[mcp_servers.openlca]
url = "http://localhost:8000/sse"
```

---

## ChatGPT Developer Mode / Apps

Use the public **`/mcp`** endpoint when creating an app in ChatGPT:

```text
https://mcp.yourdomain.com/mcp
```

Legacy `/sse` works for some MCP clients, but OpenAI’s current app connection flow expects the public MCP endpoint path.

Two requirements people miss:

1. **Enable Developer mode** (ChatGPT → Settings → Connectors → Advanced). Without it,
   custom connectors are limited to Deep Research and only call `search`/`fetch` — the
   24 openLCA tools never appear as callable actions in normal chat. After adding the
   connector, start a **new chat** and toggle it on in the composer's tools menu.
2. **Front a buffering proxy with the no-buffering gateway.** If the server sits behind
   a reverse proxy or tunnel that **buffers responses**, the connector will connect but
   show **no tools** (the stream never flushes). Deploy with `docker-compose.gateway.yml`
   and point your frontend at the gateway.
   See [online-hosting.md](online-hosting.md#path-1--tunnel-shortcut-easiest-no-custom-server).

If you set `MCP_AUTH_TOKEN` on the gateway, register the URL with the secret as a query
param (ChatGPT's UI can't send custom headers):

```text
https://mcp.yourdomain.com/mcp?api_key=<MCP_AUTH_TOKEN>
```

---

## Windsurf (Codeium)

**Config file:** `~/.codeium/windsurf/mcp_config.json`

### stdio

```json
{
  "mcpServers": {
    "openlca": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  }
}
```

### SSE

```json
{
  "mcpServers": {
    "openlca": {
      "serverType": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Continue.dev (VS Code / JetBrains extension)

**Config file:** `~/.continue/config.json`

```json
{
  "mcpServers": [
    {
      "name": "openlca",
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/openlca-mcp",
      "env": {
        "OPENLCA_PORT": "8080"
      }
    }
  ]
}
```

SSE variant:

```json
{
  "mcpServers": [
    {
      "name": "openlca",
      "url": "http://localhost:8000/sse"
    }
  ]
}
```

---

## Zed

**Config file:** `~/.config/zed/settings.json`

```json
{
  "context_servers": {
    "openlca": {
      "command": {
        "path": "python",
        "args": ["-m", "src.server"],
        "env": {
          "OPENLCA_PORT": "8080"
        }
      },
      "settings": {}
    }
  }
}
```

---

## n8n (AI Agent / MCP Tool node)

n8n typically runs in Docker. Prefer `/mcp` if your MCP node supports streamable HTTP; otherwise use the legacy SSE URL.

**If n8n and the MCP server are in the same Docker Compose stack:**
```
http://mcp-server:8000/mcp
```

**If n8n runs in its own Docker network and the MCP server is on the host:**
```
http://host.docker.internal:8000/mcp
```

**Remote (production):**
```
https://mcp.yourdomain.com/mcp
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "command not found: python" | Wrong Python name | Use `python3`, or full path: `/usr/bin/python3` |
| Server starts but no tools | Wrong `cwd` | Use absolute path; test with `cd /path && python -m src.server` |
| "Connection refused" on MCP URL | Server not running | Run `docker compose up` or `TRANSPORT=http python -m src.server` |
| "Could not connect to openLCA" | IPC server down | Open openLCA → Tools → Developer Tools → IPC Server → Start |
| Port conflict on 8000 | Another process on 8000 | Set `MCP_PORT=8001` in `.env` and update the URL in config |
| Windows: path with backslashes | JSON escape issue | Use forward slashes (`C:/Users/you/...`) or double backslashes |
| Remote connector **connects but shows no tools** (ChatGPT/Claude) | A buffering reverse proxy/tunnel swallows the MCP stream; `curl` of `/mcp/` still works because single responses aren't buffered | Front the server with the no-buffering gateway: `docker compose -f docker-compose.gateway.yml up -d` and point your frontend at it. Verify: `curl -D- --max-time 6 -H "Accept: text/event-stream" https://host/mcp/` must return `200 + text/event-stream` immediately, not `HTTP 000`. See [online-hosting.md](online-hosting.md#path-1--tunnel-shortcut-easiest-no-custom-server) |
| Remote connector tools missing in ChatGPT specifically | Developer mode off, or connector not enabled in this chat | Settings → Connectors → Advanced → enable Developer mode; start a new chat and toggle the connector on in the composer |
