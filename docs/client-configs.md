# Client Configuration

Copy-paste configs for connecting the openLCA MCP server to popular AI clients.

Two connection modes:

| Mode | How it works | When to use |
|------|-------------|-------------|
| **stdio** | Client spawns the server process directly over stdin/stdout | Claude Desktop, Cursor, VS Code — running locally |
| **SSE** | Client connects to an already-running HTTP server | Docker, n8n, remote/cloud deployments |

---

## Prerequisites

### For stdio mode — clone and install once

```bash
git clone https://github.com/dernestbank/openlca-mcp.git
cd openlca-mcp
pip install -r requirements.txt
```

Note the **absolute path** to the cloned directory — you'll need it in every config below.

- macOS/Linux: `/Users/you/openlca-mcp`
- Windows: `C:\Users\you\openlca-mcp`

### For SSE mode — server must be running first

```bash
# local Docker
docker compose up -d          # → http://localhost:8000/sse

# or direct
TRANSPORT=sse python -m src.server
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

### SSE (Docker or remote server)

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
        "--from", "git+https://github.com/dernestbank/openlca-mcp",
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

### SSE

```toml
[mcp_servers.openlca]
url = "http://localhost:8000/sse"
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

n8n typically runs in Docker. Use the Docker SSE server.

**If n8n and the MCP server are in the same Docker Compose stack:**
```
http://mcp-server:8000/sse
```

**If n8n runs in its own Docker network and the MCP server is on the host:**
```
http://host.docker.internal:8000/sse
```

**Remote (production):**
```
https://mcp.yourdomain.com/sse
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "command not found: python" | Wrong Python name | Use `python3`, or full path: `/usr/bin/python3` |
| Server starts but no tools | Wrong `cwd` | Use absolute path; test with `cd /path && python -m src.server` |
| "Connection refused" on SSE URL | Server not running | Run `docker compose up` or `TRANSPORT=sse python -m src.server` |
| "Could not connect to openLCA" | IPC server down | Open openLCA → Tools → Developer Tools → IPC Server → Start |
| Port conflict on 8000 | Another process on 8000 | Set `MCP_PORT=8001` in `.env` and update the URL in config |
| Windows: path with backslashes | JSON escape issue | Use forward slashes (`C:/Users/you/...`) or double backslashes |
