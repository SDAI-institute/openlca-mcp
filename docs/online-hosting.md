# Online Hosting Guide

> **The core constraint:** openLCA is a desktop application. It runs on a user's local machine
> and exposes an IPC server on `localhost`. There is no cloud-hosted openLCA.
> Every remote hosting strategy must account for this.

This means a "hosted MCP server" cannot actually run LCA calculations on behalf of arbitrary
users — each user's openLCA data and database live locally. The two architectures below are
the only sane options, and they solve different problems.

---

## Option A — Hosted docs and demo server

**What it is:** A public website with documentation, examples, and a live demo MCP server
connected to a *fixed* sample LCA database (e.g., a bundled ecoinvent or ELCD excerpt).
Users read the docs, try the demo, then run the real server locally against their own data.

**What it does NOT do:** It does not touch any user's openLCA installation. The demo is
read-only and runs on your server against your sample data.

### Architecture

```
Public internet
      │
      ▼
┌─────────────────────────────┐
│  Your server / VPS          │
│                             │
│  Static docs site           │  ← GitHub Pages, Netlify, Vercel, etc.
│  (README, examples, guides) │
│                             │
│  Demo MCP endpoint          │  ← docker-compose.prod.yml
│  https://demo.yourdomain.com/mcp │
│       │                     │
│  openLCA (headless*)        │  ← bundled sample database
│  IPC :8080 (localhost only) │
└─────────────────────────────┘

* openLCA has no official headless/server mode. Use a fixed openLCA instance
  running on the VPS with a GUI session or via VNC, OR a pre-populated
  olca-ipc result cache.
```

### What to host

| Asset | Where | Notes |
|-------|-------|-------|
| Documentation | GitHub Pages / Netlify | Free, auto-deploys from `docs/` |
| Demo MCP endpoint | VPS (docker-compose.prod.yml) | `https://demo.yourdomain.com/mcp` |
| Sample data | Bundled with openLCA on VPS | ELCD, ProBas, or a small custom DB |

### Quick setup

**1. Docs site (GitHub Pages)**

Enable GitHub Pages on the repo → source: `docs/` branch or folder.
The existing `docs/` directory becomes your public docs site instantly.

**2. Demo server**

```bash
# On your VPS
git clone https://github.com/SDAI-institute/openlca-mcp.git
cd openlca-mcp

# Configure
cp .env.example .env
# Set: MCP_DOMAIN=demo.yourdomain.com, ACME_EMAIL=..., OPENLCA_HOST=localhost

# Prep Let's Encrypt storage
mkdir -p docker/letsencrypt
touch docker/letsencrypt/acme.json
chmod 600 docker/letsencrypt/acme.json

# Start (openLCA must already be running on this VPS with a sample database)
docker compose -f docker-compose.prod.yml up -d
```

Users can now point modern MCP clients at `https://demo.yourdomain.com/mcp` and legacy SSE clients at `https://demo.yourdomain.com/sse`, then run
queries against your sample data.

### Limitations

- Users are querying **your** database, not theirs
- openLCA on a headless Linux VPS requires a display (use Xvfb or VNC)
- All users share one openLCA connection — no isolation, no auth by default
  (add Traefik Basic Auth if needed, see [DOCKER.md](../DOCKER.md))
- Write operations (`create_process`, `create_product_system`, etc.) would
  mutate the shared demo database — consider disabling write tools for the demo

### When to choose this

- You want to showcase the MCP server without asking users to install anything
- You are building documentation or a course
- You want a playground for testing prompts before running against real data

---

## Option B — Cloud relay with local agent

**What it is:** A cloud service that acts as a broker. Users install a small local
"bridge" process on their machine. The bridge connects *outbound* to your cloud relay,
which forwards MCP calls from AI clients back through the bridge to the user's local
openLCA. No inbound firewall rules needed on the user's side.

**What it DOES do:** Lets any AI client use a single public URL while actually
controlling each user's own openLCA installation.

### Architecture

```
AI Client (Claude, Cursor, etc.)
      │  MCP over HTTPS
      ▼
┌─────────────────────────────────┐
│  Cloud Relay                    │
│  https://api.yourdomain.com/mcp │
│                                 │
│  - Session routing              │
│  - Auth (API keys / OAuth)      │
│  - WebSocket hub                │
└────────────┬────────────────────┘
             │  WebSocket (outbound from user)
             ▼
┌─────────────────────────────────┐
│  Local Bridge (user installs)   │
│  tiny Python/Node process       │
│  connects outbound → no inbound │
│  firewall rules needed          │
└────────────┬────────────────────┘
             │  IPC :8080 (localhost)
             ▼
┌─────────────────────────────────┐
│  openLCA Desktop + database     │
│  (user's machine)               │
└─────────────────────────────────┘
```

### Three implementation paths

#### Path 1 — Tunnel shortcut (easiest, no custom server)

Use any tunneling service or reverse proxy to expose the user's local MCP server.
The user runs both openLCA and the MCP server locally, then opens a tunnel.

```
AI Client → https://<your-tunnel-host>/mcp → tunnel → gateway (no buffering) → local MCP → openLCA
```

> ⚠️ **Critical gotcha — buffering proxies break MCP.** MCP's Streamable-HTTP/SSE
> transports are long-lived streams. A **reverse proxy or tunnel that buffers
> responses** never flushes the stream headers, so a remote connector (ChatGPT,
> Claude) connects but shows **no tools** — it reports the server as "visible as
> text, not an attached tool." A `curl` of `initialize`/`tools/list` still works
> (those are single responses), which makes this easy to misdiagnose. Some hosted
> CDN tunnels buffer by default; self-hosted proxies vary by config.
>
> **Fix:** put a reverse proxy that disables buffering between the frontend and the
> server. This repo ships one — `docker-compose.gateway.yml` + `gateway/Caddyfile`
> (`flush_interval -1`). Point your tunnel at the **gateway**, not the bare server.
>
> The decisive test (replace the host as appropriate):
> ```bash
> # Through your public host, the streaming endpoint must return headers IMMEDIATELY:
> curl -sS -D - -o /dev/null --max-time 6 \
>   -H "Accept: text/event-stream" https://<your-tunnel-host>/mcp/
> # GOOD: HTTP/1.1 200 + content-type: text/event-stream  (then it holds open)
> # BAD : HTTP 000 / times out with 0 bytes  →  the frontend is buffering
> ```

**User steps (with the streaming-safe gateway):**
```bash
# 1. Configure
cp .env.example .env
#   set OPENLCA_HOST=host.docker.internal  (openLCA runs on this machine)
#   optionally set MCP_AUTH_TOKEN (openssl rand -hex 32) to require a secret

# 2. Start the MCP server behind the no-buffering Caddy gateway
docker compose -f docker-compose.gateway.yml up -d --build   # gateway → 127.0.0.1:8030

# 3. Expose the GATEWAY (port 8030), NOT the bare server, with your tunnel of choice:
ngrok http 8030                          # → https://xxxx.ngrok.io/mcp
tailscale serve http://localhost:8030    # → https://hostname.tailnet.ts.net/mcp
#   ...or any tunnel/reverse proxy pointed at http://127.0.0.1:8030

# Use https://<your-host>/mcp in ChatGPT/Claude/OpenAI apps
# Use https://<your-host>/sse for legacy SSE clients
# If MCP_AUTH_TOKEN is set, append ?api_key=<token> to the URL.
```

If your tunnel/proxy already streams without buffering you can point it straight at
the bare server (`:8000`) instead — but routing through the gateway is harmless,
guarantees streaming, and adds optional auth, so it is the safe default.

**Pros:** Zero custom backend code, works immediately  
**Cons:** URL may change on restart (free tiers); user must manage the tunnel;
a buffering frontend requires the no-buffering gateway above

---

#### Path 2 — Persistent relay service (production-grade)

Build a small relay server that maintains a WebSocket hub. Users register a session
and the local bridge connects to it. AI clients use stable per-user URLs.

**Relay server** (your cloud, rough sketch in Python):

```python
# relay/server.py — runs on your VPS
# Handles two sides:
#   /register  — local bridge connects here (WebSocket, outbound from user)
#   /mcp/{session_id}/sse — AI clients connect here

from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

sessions: dict[str, WebSocket] = {}

async def bridge_ws(ws: WebSocket):
    """Local bridge connects here to register a session."""
    await ws.accept()
    session_id = ws.query_params["session_id"]
    sessions[session_id] = ws
    try:
        await ws.receive_text()   # keep open until bridge disconnects
    finally:
        sessions.pop(session_id, None)

async def mcp_sse(request):
    """AI clients connect here; calls are forwarded to the registered bridge."""
    session_id = request.path_params["session_id"]
    bridge = sessions.get(session_id)
    if not bridge:
        return JSONResponse({"error": "no active session"}, status_code=503)
    # ... forward MCP SSE stream through bridge WebSocket ...
```

**Local bridge** (user installs once, ships as a small Python/Node package):

```python
# bridge/client.py — runs on user's machine
import asyncio, websockets, json

RELAY_URL = "wss://api.yourdomain.com/register"
LOCAL_MCP  = "http://localhost:8000"   # local MCP SSE server

async def run(session_id: str, api_key: str):
    async with websockets.connect(
        f"{RELAY_URL}?session_id={session_id}&key={api_key}"
    ) as ws:
        print(f"Connected. Use: https://api.yourdomain.com/mcp/{session_id}/sse")
        async for message in ws:
            # forward MCP call to local server, send response back
            ...
```

**Pros:** Stable per-user URLs, full auth control, no tunnel tools needed  
**Cons:** Requires building and maintaining the relay + bridge packages

---

#### Path 3 — Tailscale / private VPN (team use)

For teams where everyone is on the same Tailscale network (or a WireGuard VPN),
each user's local MCP server is addressable by stable Tailscale IP or hostname.

```
AI Client → https://user-machine.tailnet.ts.net/mcp → local MCP server → openLCA
```

**Setup per user:**
```bash
# Enable Tailscale HTTPS (requires Tailscale account)
tailscale serve --https=443 http://localhost:8000
# Server is now at: https://user-machine.tailnet.ts.net/mcp
```

No relay server needed. Stable URLs. Works well for research groups and companies.

---

### Comparison

| | Tunnel shortcut | Relay service | Tailscale |
|---|---|---|---|
| Setup complexity | Low | High | Medium |
| Custom backend | No | Yes | No |
| Stable URLs | No (free tier) | Yes | Yes |
| Auth control | Tunnel only | Full | Tailscale ACLs |
| Per-user isolation | Yes | Yes | Yes |
| Requires user action | Run tunnel cmd | Install bridge | Install Tailscale |
| Best for | Quick demos | SaaS product | Teams / labs |

---

## Choosing between A and B

| Goal | Use |
|------|-----|
| Show what the MCP server can do, without user installs | Option A (demo server with sample data) |
| Let users try a live demo with real LCA data | Option B Path 1 (tunnel, lowest friction) |
| Build a product where users control their own openLCA remotely | Option B Path 2 (relay service) |
| Research group / internal team sharing | Option B Path 3 (Tailscale) |
| Publish the docs as a website | Option A (GitHub Pages) |

---

## Security considerations for any public endpoint

- **The MCP server has write access to openLCA.** `create_process`, `create_product_system`,
  and other write tools can modify the openLCA database. For public demos, disable or
  restrict write tools.
- Add **Basic Auth or API key** middleware before exposing any endpoint publicly:
  the bundled gateway (`docker-compose.gateway.yml`) enforces a shared secret when
  `MCP_AUTH_TOKEN` is set (accepted as `?api_key=` — the only form ChatGPT's connector
  UI supports — or `Authorization: Bearer`); or use Traefik Basic Auth labels in
  `docker-compose.prod.yml`.
- For the relay path, issue **per-user API keys** and rotate them — never share a single
  key across users.
- The local bridge only connects *outbound* (to your relay), so users do not need to open
  any inbound firewall ports.
