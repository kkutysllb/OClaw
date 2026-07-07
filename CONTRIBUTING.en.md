# Contributing Guide

Thank you for your interest in OClaw! This document will help you set up your development environment and understand the development workflow.

**English** | [简体中文](./CONTRIBUTING.md)

## Development Environment Setup

We provide two development environments. **Docker is recommended** for the most consistent and hassle-free experience.

### Option 1: Docker Development (Recommended)

Docker provides a consistent, isolated environment with all dependencies pre-configured — no need to install Node.js, Python, or nginx on your local machine.

#### Prerequisites

- Docker Desktop or Docker Engine
- pnpm (for cache optimization)

#### Setup Steps

1. **Configure the application**:
   ```bash
   # Copy example config
   cp config.example.yaml config.yaml

   # Set your API key
   export OPENAI_API_KEY="your-key-here"
   # Or edit config.yaml directly
   ```

2. **Initialize Docker environment** (first time only):
   ```bash
   make docker-init
   ```
   This command will:
   - Build Docker images
   - Install frontend dependencies (pnpm)
   - Install backend dependencies (uv)
   - Share pnpm cache with the host for faster subsequent builds

3. **Start development services**:
   ```bash
   make docker-start
   ```

   All services start with hot reload:
   - Frontend changes auto-refresh
   - Backend changes auto-trigger restart
   - LangGraph service supports hot reload

4. **Access the application**:
   - Web UI: http://localhost:9191
   - API Gateway: http://localhost:9191/api/*
   - LangGraph: http://localhost:9191/api/langgraph/*

#### Docker Commands

```bash
# Verify the Docker environment is ready
make docker-init
# Start Docker services (localhost:9191)
make docker-start
# Stop Docker development services
make docker-stop
# View Docker development logs
make docker-logs
# View Docker frontend logs
make docker-logs-frontend
# View Docker gateway logs
make docker-logs-gateway
```

If Docker builds are slow in your network environment, override the default package registries before running `make docker-init` or `make docker-start`:

```bash
export UV_INDEX_URL=https://pypi.org/simple
export NPM_REGISTRY=https://registry.npmjs.org
```

#### Recommended Host Resources

Below are practical starting references for development and review environments:

| Scenario | Starting Config | Recommended Config | Notes |
|---------|-----------|------------|-------|
| `make dev` single-machine dev | 4 vCPU, 8 GB RAM | 8 vCPU, 16 GB RAM | Best with hosted model APIs. |
| `make docker-start` review environment | 4 vCPU, 8 GB RAM | 8 vCPU, 16 GB RAM | Docker image builds need more space. |
| Shared Linux test server | 8 vCPU, 16 GB RAM | 16 vCPU, 32 GB RAM | Suitable for heavier multi-agent runs or multi-reviewer scenarios. |

`2 vCPU / 4 GB` environments typically cannot start reliably or become unresponsive under normal OClaw load.

#### Linux: Docker Daemon Permission Denied

If `make docker-init`, `make docker-start`, or `make docker-stop` fail on Linux with an error like the following, the current user may not have permission to access the Docker daemon socket:

```text
unable to get image 'kkoclaw-dev-langgraph': permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

Recommended fix: add the current user to the `docker` group so Docker commands can run without `sudo`.

1. Confirm the `docker` group exists:
   ```bash
   getent group docker
   ```
2. Add the current user to the `docker` group:
   ```bash
   sudo usermod -aG docker $USER
   ```
3. Apply the new group membership. The most reliable method is to fully log out and log back in. To refresh the current shell session, run:
   ```bash
   newgrp docker
   ```
4. Verify Docker access:
   ```bash
   docker ps
   ```
5. Retry the OClaw command:
   ```bash
   make docker-stop
   make docker-start
   ```

If `docker ps` still reports a permission error after running `usermod`, log out completely and log back in before retrying.

#### Docker Architecture

```
Host
  ↓
Docker Compose (kkoclaw-dev)
  ├→ nginx (port 9191) ← reverse proxy
  ├→ frontend (port 9192) ← frontend, hot reload
  ├→ gateway (port 9193) ← gateway API, hot reload
```

**Advantages of Docker development**:
- ✅ Consistent environment across machines
- ✅ No need to install Node.js, Python, or nginx locally
- ✅ Isolated dependencies and services
- ✅ Easy to clean up and reset
- ✅ Hot reload for all services
- ✅ Production-like environment

### Option 2: Local Development

If you prefer running services directly on the host machine:

#### Prerequisites

Check that all required tools are installed:

```bash
make check
```

Required tools:
- Node.js 22+
- pnpm
- uv (Python package manager)
- nginx

#### Setup Steps

1. **Configure the application** (same as Docker above)

2. **Install dependencies** (also sets up pre-commit hooks):
   ```bash
   make install
   ```

3. **Run development servers** (starts all services via nginx):
   ```bash
   make dev
   ```

4. **Access the application**:
   - Web UI: http://localhost:9191
   - All API requests are automatically proxied through nginx

#### Manual Service Control

If you need to start services individually:

1. **Start backend services**:
   ```bash
   # Terminal 1: Start Gateway API (port 9193)
   cd backend
   make dev

   # Terminal 2: Start frontend (port 9192)
   cd frontend
   pnpm dev
   ```

2. **Start nginx**:
   ```bash
   make nginx
   # Or directly: nginx -c $(pwd)/docker/nginx/nginx.local.conf -g 'daemon off;'
   ```

3. **Access the application**:
   - Web UI: http://localhost:9191

#### Nginx Configuration

The nginx configuration provides:
- Unified entry port 9191
- Routes `/api/langgraph/*` to Gateway API (9193)
- Routes other `/api/*` endpoints to Gateway API (9193)
- Routes non-API requests to frontend (9192)
- Centralized CORS handling
- SSE/streaming support for agent real-time responses
- Optimized timeout settings for long-running operations

## Project Structure

```
kkoclaw/
├── config.example.yaml              # Config template
├── extensions_config.example.json   # MCP and Skills config template
├── Makefile                         # Build and dev commands
├── scripts/
│   └── docker.sh                   # Docker management script
├── docker/
│   ├── docker-compose-dev.yaml     # Docker Compose config
│   └── nginx/
│       ├── nginx.conf              # Docker Nginx config
│       └── nginx.local.conf        # Local dev Nginx config
├── backend/                        # Backend application
│   ├── src/
│   │   ├── gateway/                # Gateway API (port 9193)
│   │   ├── mcp/                    # Model Context Protocol integration
│   │   ├── skills/                 # Skill system
│   │   └── sandbox/                # Sandbox execution
│   ├── docs/                       # Backend documentation
│   └── Makefile                    # Backend commands
├── frontend/                       # Frontend application
│   └── Makefile                    # Frontend commands
└── skills/                         # Agent skills
    ├── public/                     # Public skills
    └── custom/                     # Custom skills
```

## Architecture

```
Browser
  ↓
Nginx (port 9191) ← Unified entry
  ├→ Frontend (port 9192) ← / (non-API requests)
  ├→ Gateway API (port 9193) ← /api/models, /api/mcp, /api/skills, /api/threads/*/artifacts
  └→ Gateway Runtime (port 9193) ← /api/langgraph/* (agent interaction)
```

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make code changes** (hot reload supported)

3. **Format and lint** (CI will reject unformatted code):
   ```bash
   # Backend
   cd backend
   make format   # ruff check --fix + ruff format

   # Frontend
   cd frontend
   pnpm format:write   # Prettier
   ```

4. **Test your changes thoroughly**

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: describe your changes"
   ```

6. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Testing

```bash
# Backend tests
cd backend
make test

# Frontend unit tests
cd frontend
make test

# Frontend E2E tests (requires Chromium; builds and auto-starts Next.js production server)
cd frontend
make test-e2e
```

### PR Regression Checks

Each Pull Request triggers the following CI workflows:

- **Backend Unit Tests** — [.github/workflows/backend-unit-tests.yml](.github/workflows/backend-unit-tests.yml)
- **Frontend Unit Tests** — [.github/workflows/frontend-unit-tests.yml](.github/workflows/frontend-unit-tests.yml)
- **Frontend E2E Tests** — [.github/workflows/e2e-tests.yml](.github/workflows/e2e-tests.yml) (triggered only on `frontend/` directory changes)

## Code Style

- **Backend (Python)**: We use `ruff` for linting and formatting. Run `make format` before committing.
- **Frontend (TypeScript)**: We use ESLint and Prettier. Run `pnpm format:write` before committing.
- CI enforces code formatting — unformatted code will cause lint checks to fail.

## Documentation

- [Configuration Guide](backend/docs/CONFIGURATION.md) — Setup and configuration
- [Architecture Overview](backend/CLAUDE.md) — Technical architecture
- [MCP Setup Guide](backend/docs/MCP_SERVER.md) — Model Context Protocol configuration

## Need Help?

- Check existing [Issues](https://github.com/OClaw/kkoclaw/issues)
- Read the [documentation](backend/docs/)
- Ask in [Discussions](https://github.com/OClaw/kkoclaw/discussions)

## License

By contributing to OClaw, you agree that your contributions will be licensed under the [MIT License](./LICENSE).
