# OClaw Installation Guide

This file is intended for coding agents. If the OClaw repository is not yet cloned and open, clone the repository first, then continue from the repository root.

**English** | [简体中文](./Install.md)

## Objective

Set up an OClaw local development workspace on the user's machine with the lowest possible risk.

Default preferences:

1. Docker development environment
2. Local development environment

Do not assume API keys or model credentials already exist. Set up everything that can be safely prepared, then stop and briefly summarize what the user still needs to provide.

## Operating Rules

- Keep it idempotent. Re-running this document should not break existing setups.
- Prefer existing repository commands over ad-hoc shell commands.
- Do not use `sudo` or install system packages without the user's explicit consent.
- Do not overwrite existing user configuration values unless the user requests it.
- If a step fails, stop, explain the obstacle, and provide the minimal next action.
- If multiple setup paths exist, prefer Docker when already available.

## Success Criteria

Setup is considered successful when all of the following conditions are met:

- The OClaw repository is cloned, and the current working directory is the repository root.
- `config.yaml` exists.
- For Docker setups, `make docker-init` has completed successfully, Docker prerequisites are ready, but services are not assumed to be running yet.
- For local setups, `make check` has passed or reports no missing prerequisites, and `make install` has completed successfully.
- The user has received the exact next command to start OClaw.
- The user has also received any missing model configuration or referenced environment variable names in `config.yaml`, without checking the actual values of files containing keys.

## Steps

- If the current directory is not the OClaw repository root, clone the repository first, then switch to the repository root.
- Verify that `Makefile`, `backend/`, `frontend/`, and `config.example.yaml` exist to confirm the current directory is the OClaw repository root.
- Detect whether `config.yaml` already exists.
- If `config.yaml` does not exist, run `make config`.
- Detect whether Docker is available and whether the daemon is accessible via `docker info`.
- If Docker is available:
  - Run `make docker-init`.
  - This is only considered Docker prerequisites preparation. Do not claim that application services, compose validation, or image builds have been successful.
  - Do not start long-running services unless the user explicitly requests it or the setup request explicitly includes startup verification.
  - Tell the user the recommended next command is `make docker-start`.
- If Docker is unavailable:
  - Run `make check`.
  - If `make check` reports missing system dependencies (such as `node`, `pnpm`, `uv`, or `nginx`), stop and report the missing tools rather than attempting privileged installation.
  - If prerequisites are met, run `make install`.
  - Tell the user the recommended next command is `make dev`.
- Only check `config.yaml` for missing model entries or referenced environment variable placeholders. Do not read `.env`, `frontend/.env`, or other files containing keys.
- If no models are configured, tell the user that at least one entry must be added under `models` in `config.yaml`.
- If `config.yaml` references variables like `$OPENAI_API_KEY`, tell the user which variable names still need real values, but do not verify them by opening files containing keys.
- If the repository appears already configured, avoid repeating expensive work unless verifying the environment is necessary.

## Verification

Use the lightest verification that matches the chosen setup path.

For Docker setups:

- Confirm that `make docker-init` completed successfully.
- Confirm that `config.yaml` exists.
- Explicitly state that Docker services are not yet started, and `make docker-start` remains the first real startup step.
- Do not keep background services running unless the user requests it.

For local setups:

- Confirm that `make install` completed successfully.
- Confirm that `config.yaml` exists.
- Do not keep background services running unless the user requests it.

## Final Response Format

Return a brief report containing:

1. Setup path used: Docker or local
2. Level of setup achieved: Docker prerequisites prepared or local dependencies installed
3. Files created or detected: e.g. `config.yaml`
4. Actions the user still needs to perform: model configuration, environment variable values, authentication files, or none
5. The exact next command to start OClaw

## Execute Immediately

Complete the steps above. When finished, stop at the setup boundary and report status, rather than continuing into unrelated project work.
