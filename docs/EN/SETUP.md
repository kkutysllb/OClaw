# Setup Guide

Quick setup instructions for OClaw.

## Configuration Setup

OClaw uses a YAML configuration file that should be placed in the **project root directory**.

### Steps

1. **Enter project root directory**:
   ```bash
   cd /path/to/kk-oclaw
   ```

2. **Copy example configuration**:
   ```bash
   cp config.example.yaml config.yaml
   ```

3. **Edit configuration**:
   ```bash
   # Method A: Set environment variable (recommended)
   export OPENAI_API_KEY="your-key-here"

   # Optional: specify project root when running from other directories
   export OClaw_PROJECT_ROOT="/path/to/kk-oclaw"

   # Method B: Edit config.yaml directly
   vim config.yaml  # or your preferred editor
   ```

4. **Verify configuration**:
   ```bash
   cd backend
   python -c "from kkoclaw.config import get_app_config; print('✓ Config loaded:', get_app_config().models[0].name)"
   ```

## Important Notes

- **Location**: `config.yaml` should be placed in `kk-oclaw/` (project root directory)
- **Git**: `config.yaml` is automatically ignored by git (contains secrets)
- **Runtime root**: If OClaw may be launched from outside the project root, set `OClaw_PROJECT_ROOT`
- **Runtime data**: State is saved by default in the `.kkoclaw` directory under the project root; set `OClaw_HOME` to change the location
- **Skill directory**: Skills are located by default in the `skills/` directory under the project root; set `OClaw_SKILLS_PATH` or `skills.path` to change

## Configuration File Search Order

The backend searches for `config.yaml` in the following order:

1. `config_path` parameter explicitly passed in code
2. `OClaw_CONFIG_PATH` environment variable (if set)
3. `config.yaml` under `OClaw_PROJECT_ROOT`, or the current working directory if `OClaw_PROJECT_ROOT` is not set
4. Legacy backend/repo root locations retained for monorepo compatibility

**Recommendation**: Place `config.yaml` in the project root (`kk-oclaw/config.yaml`)

## Sandbox Setup (Optional but Recommended)

If you plan to use Docker/container sandbox (configure `sandbox.use: kkoclaw.community.aio_sandbox:AioSandboxProvider` in `config.yaml`), it is strongly recommended to pull the container image in advance:

```bash
# Run from project root
make setup-sandbox
```

**Why pull in advance?**
- Sandbox images (~500MB+) are pulled on first use, causing a long wait
- Pulling in advance shows clear progress indicators
- Avoids confusion on first agent use

If this step is skipped, the image will be automatically pulled on first agent execution, which may take several minutes depending on your network speed.

## Troubleshooting

### Configuration File Not Found

```bash
# Check where the backend is looking
cd kk-oclaw/backend
python -c "from kkoclaw.config.app_config import AppConfig; print(AppConfig.resolve_config_path())"
```

If configuration is not found:
1. Ensure `config.example.yaml` has been copied to `config.yaml`
2. Confirm you are in the project root, or have set `OClaw_PROJECT_ROOT`
3. Check if the file exists: `ls -la config.yaml`

### Permission Denied

```bash
chmod 600 ../config.yaml  # Protect sensitive configuration
```

## Related Documentation

- [Configuration Guide](CONFIGURATION.md) — Detailed configuration options
- [Architecture Overview](../CLAUDE.md) — System architecture
