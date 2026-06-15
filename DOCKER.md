# Docker Setup

Three deployment modes are supported:

| Mode | File | Use case |
|------|------|----------|
| Direct (no Docker) | — | Claude Desktop, local scripts |
| Local Docker | `docker-compose.yml` | Containerised n8n, local testing |
| Production | `docker-compose.prod.yml` | Live domain, HTTPS, remote access |

---

## Prerequisites

- Docker Engine 24+ and Docker Compose v2 (`docker compose`)
- openLCA desktop running with **IPC server enabled**
  - openLCA → Tools → Developer Tools → IPC Server → Start (default port 8080)

---

## 1. Direct (no Docker)

For Claude Desktop or any local client that communicates via stdin/stdout:

```bash
pip install -r requirements.txt
python -m src.server          # TRANSPORT=stdio by default
```

Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "openlca": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/openlca_mcp"
    }
  }
}
```

---

## 2. Local Docker (SSE over HTTP)

openLCA runs on your host machine; the MCP server runs in a container and reaches it via `host.docker.internal`.

```bash
cp .env.example .env          # adjust OPENLCA_PORT if needed

docker compose up --build
```

**Endpoints:**
- MCP SSE: `http://localhost:8000/sse`
- Health:   `http://localhost:8000/health`

**n8n MCP node config:**
```json
{
  "serverType": "sse",
  "url": "http://localhost:8000/sse"
}
```

> **Linux note:** `extra_hosts: host.docker.internal:host-gateway` is already in `docker-compose.yml`. Docker Desktop on Mac/Windows resolves `host.docker.internal` automatically.

---

## 3. Production (domain + HTTPS)

Traefik handles SSL termination via Let's Encrypt. openLCA can be on the same host or a remote machine.

### 3a. Prepare

```bash
# 1. Point your domain DNS A-record to this server's public IP and wait for propagation
# 2. Configure environment
cp .env.example .env
```

Edit `.env`:
```bash
OPENLCA_HOST=host.docker.internal   # same host, or set to remote IP/hostname
OPENLCA_PORT=8080
MCP_DOMAIN=mcp.yourdomain.com
ACME_EMAIL=you@yourdomain.com
LOG_LEVEL=INFO
```

```bash
# 3. Create Let's Encrypt storage (must be chmod 600)
mkdir -p docker/letsencrypt
touch docker/letsencrypt/acme.json
chmod 600 docker/letsencrypt/acme.json
```

### 3b. Start

```bash
docker compose -f docker-compose.prod.yml up -d
```

**Endpoints:**
- MCP SSE: `https://mcp.yourdomain.com/sse`
- Health:   `https://mcp.yourdomain.com/health`

### 3c. Optional: HTTP Basic Auth

Generate credentials (requires `apache2-utils` / `httpd-tools`):
```bash
htpasswd -nb myuser mysecretpassword
# output: myuser:$apr1$...
# Double every $ for docker compose: myuser:$$apr1$$...
```

Add to `.env`:
```bash
MCP_BASIC_AUTH=myuser:$$apr1$$...
```

Uncomment the two `basicauth` label lines in `docker-compose.prod.yml`.

### 3d. openLCA on a remote machine

If openLCA runs on a different server than Docker, set:
```bash
OPENLCA_HOST=192.168.1.50    # LAN IP, or public IP/hostname
```

Make sure port 8080 is reachable from the Docker host (firewall rules / VPN).

---

## Logs and management

```bash
# Follow logs
docker compose logs -f mcp-server

# Restart after code change
docker compose up --build -d

# Stop everything
docker compose down

# Production teardown (keeps volumes)
docker compose -f docker-compose.prod.yml down
```

---

## Environment variable reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSPORT` | `stdio` | `stdio` or `sse` |
| `OPENLCA_HOST` | `localhost` | Host running openLCA IPC server |
| `OPENLCA_PORT` | `8080` | openLCA IPC port |
| `MCP_HOST` | `0.0.0.0` | Bind address for SSE HTTP server |
| `MCP_PORT` | `8000` | Port for SSE HTTP server |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MCP_DOMAIN` | — | Production domain (Traefik label) |
| `ACME_EMAIL` | — | Let's Encrypt contact email |
| `MCP_BASIC_AUTH` | — | Optional `user:$$hash` for basic auth |
