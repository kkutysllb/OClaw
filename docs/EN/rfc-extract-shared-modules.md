# RFC: Extract Shared Skill Installer and Upload Manager to Harness

## 1. Problem

The Gateway (`app/gateway/routers/skills.py`, `uploads.py`) and Client (`kkoclaw/client.py`) have each independently implemented the same business logic:

### Skill Installation

| Logic | Gateway (`skills.py`) | Client (`client.py`) |
|-------|----------------------|---------------------|
| Zip Safety Check | `_is_unsafe_zip_member()` | Inline `Path(info.filename).is_absolute()` |
| Symlink Filtering | `_is_symlink_member()` | Post-extract `p.is_symlink()` delete |
| Zip Bomb Defense | `total_size += info.file_size` (declared) | `total_size > 100MB` (declared) |
| macOS Metadata Filtering | `_should_ignore_archive_entry()` | None |
| Frontmatter Validation | `_validate_skill_frontmatter()` | `_validate_skill_frontmatter()` |
| Duplicate Detection | `HTTPException(409)` | `ValueError` |

**Two implementations, inconsistent behavior**: Gateway streams writes and tracks real unpacked size; Client accumulates declared `file_size`. Gateway skips symlinks during extraction; Client extracts everything then traverses and deletes symlinks.

### Upload Management

| Logic | Gateway (`uploads.py`) | Client (`client.py`) |
|-------|----------------------|---------------------|
| Directory Access | `get_uploads_dir()` + `mkdir` | `_get_uploads_dir()` + `mkdir` |
| Filename Safety | Inline `Path(f).name` + manual check | No check, directly uses `src_path.name` |
| Duplicate Handling | None (overwrite) | None (overwrite) |
| Listing | Inline `iterdir()` | Inline `os.scandir()` |
| Deletion | Inline `unlink()` + traversal check | Inline `unlink()` + traversal check |
| Path Traversal | `resolve().relative_to()` | `resolve().relative_to()` |

**The same traversal check written twice** — any security fix must be applied to two places.

## 2. Design Principles

### Dependency Direction

```
app.gateway.routers.skills  ──┐
app.gateway.routers.uploads ──┤── calls ──→  kkoclaw.skills.installer
kkoclaw.client             ──┘              kkoclaw.uploads.manager
```

- Shared modules live at the harness layer (`kkoclaw.*`), pure business logic, no FastAPI dependency
- Gateway handles HTTP adaptation (`UploadFile` → bytes, exceptions → `HTTPException`)
- Client handles local adaptation (`Path` → copy, exceptions → Python exceptions)
- Satisfies `test_harness_boundary.py` constraint: harness never imports app

### Exception Strategy

| Shared Layer Exception | Gateway Mapped To | Client |
|----------------------|-----------------|--------|
| `FileNotFoundError` | `HTTPException(404)` | Propagated |
| `ValueError` | `HTTPException(400)` | Propagated |
| `SkillAlreadyExistsError` | `HTTPException(409)` | Propagated |
| `PermissionError` | `HTTPException(403)` | Propagated |

Replace string-type routing (`"already exists" in str(e)`) with typed exception matching (`SkillAlreadyExistsError`).

## 3. New Modules

### 3.1 `kkoclaw.skills.installer`

```python
# Security checks
is_unsafe_zip_member(info: ZipInfo) -> bool    # Absolute path / .. traversal
is_symlink_member(info: ZipInfo) -> bool        # Unix symlink detection
should_ignore_archive_entry(path: Path) -> bool # __MACOSX / dotfiles

# Extraction
safe_extract_skill_archive(zip_ref, dest_path, max_total_size=512MB)
  # Streamed writes, accumulating real bytes (vs declared file_size)
  # Dual traversal check: member-level + resolve-level

# Directory resolution
resolve_skill_dir_from_archive(temp_path: Path) -> Path
  # Auto-enter single directory, filter macOS metadata

# Install entry point
install_skill_from_archive(zip_path, *, skills_root=None) -> dict
  # is_file() pre-check before extension validation
  # SkillAlreadyExistsError replaces ValueError

# Exceptions
class SkillAlreadyExistsError(ValueError)
```

### 3.2 `kkoclaw.uploads.manager`

```python
# Directory management
get_uploads_dir(thread_id: str) -> Path      # Pure path, no side effects
ensure_uploads_dir(thread_id: str) -> Path   # Create directory (for write paths)

# Filename safety
normalize_filename(filename: str) -> str
  # Path.name extraction + reject ".." / "." / backslashes / >255 bytes
deduplicate_filename(name: str, seen: set) -> str
  # _N suffix increment dedup, in-place seen mutation

# Path safety
validate_path_traversal(path: Path, base: Path) -> None
  # resolve().relative_to(), raises PermissionError on failure

# File operations
list_files_in_dir(directory: Path) -> dict
  # scandir + stat in context (no duplicate stat)
  # follow_symlinks=False prevents metadata leaks
  # Non-existent directories return empty list
delete_file_safe(base_dir: Path, filename: str) -> dict
  # Validate traversal first, then unlink

# URL helpers
upload_artifact_url(thread_id, filename) -> str   # Percent-encoded for HTTP safety
upload_virtual_path(filename) -> str               # Sandbox-internal path
enrich_file_listing(result, thread_id) -> dict     # Add URLs, stringify sizes
```

## 4. Changes

### 4.1 Gateway Slimming

**`app/gateway/routers/skills.py`**:
- Remove `_is_unsafe_zip_member`, `_is_symlink_member`, `_safe_extract_skill_archive`, `_should_ignore_archive_entry`, `_resolve_skill_dir_from_archive_root` (~80 lines)
- `install_skill` route becomes a single call to `install_skill_from_archive(path)`
- Exception mapping: `SkillAlreadyExistsError → 409`, `ValueError → 400`, `FileNotFoundError → 404`

**`app/gateway/routers/uploads.py`**:
- Remove inline `get_uploads_dir` (replaced by `ensure_uploads_dir`/`get_uploads_dir`)
- `upload_files` uses `normalize_filename()` instead of inline safety check
- `list_uploaded_files` uses `list_files_in_dir()` + enrichment
- `delete_uploaded_file` uses `delete_file_safe()` + companion markdown cleanup

### 4.2 Client Slimming

**`kkoclaw/client.py`**:
- Remove `_get_uploads_dir` static method
- Remove ~50 lines of inline zip handling in `install_skill`
- `install_skill` delegates to `install_skill_from_archive()`
- `upload_files` uses `deduplicate_filename()` + `ensure_uploads_dir()`
- `list_uploads` uses `get_uploads_dir()` + `list_files_in_dir()`
- `delete_upload` uses `get_uploads_dir()` + `delete_file_safe()`
- `update_mcp_config` / `update_skill` now resets `_agent_config_key = None`

### 4.3 Read/Write Path Separation

| Operation | Function | Creates Directory? |
|-----------|----------|:------------:|
| Upload (write) | `ensure_uploads_dir()` | Yes |
| List (read) | `get_uploads_dir()` | No |
| Delete (read) | `get_uploads_dir()` | No |

Read paths no longer have `mkdir` side effects — non-existent directories return an empty list.

## 5. Security Improvements

| Improvement | Before | After |
|-------------|--------|-------|
| Zip bomb detection | Sum of declared `file_size` | Streamed writes, accumulate real bytes |
| Symlink handling | Gateway skips / Client post-extract delete | Unified skip + log |
| Traversal check | Member-level only | Member-level + `resolve().is_relative_to()` |
| Filename backslashes | Gateway checks / Client doesn't | Unified reject |
| Filename length | No check | Reject > 255 bytes (OS limit) |
| thread_id validation | None | Reject unsafe filesystem characters |
| Listing symlink leak | `follow_symlinks=True` (default) | `follow_symlinks=False` |
| 409 status routing | `"already exists" in str(e)` | `SkillAlreadyExistsError` type match |
| Artifact URL encoding | Raw filenames in URLs | `urllib.parse.quote()` |

## 6. Considered Alternatives

| Alternative | Why Not |
|-------------|---------|
| Keep logic in Gateway, Client calls Gateway via HTTP | Adds network dependency for embedded Client; defeats the purpose of `OClawClient` as an in-process API |
| Abstract base class with Gateway/Client subclasses | Over-engineered for pure functions; no polymorphism needed |
| Move everything into `client.py`, have Gateway import it | Violates harness/app boundary — Client is in harness, but Gateway-specific models (Pydantic response types) should stay in the app layer |
| Merge Gateway and Client into one module | They serve different consumers (HTTP vs in-process) with different adaptation needs |

## 7. Breaking Changes

**None.** All public APIs (Gateway HTTP endpoints, `OClawClient` methods) retain their existing signatures and return formats. `SkillAlreadyExistsError` is a subclass of `ValueError`, so existing `except ValueError` handlers still catch it.

## 8. Testing

| Module | Test File | Count |
|--------|-----------|:-----:|
| `skills.installer` | `tests/test_skills_installer.py` | 22 |
| `uploads.manager` | `tests/test_uploads_manager.py` | 20 |
| `client` hardening | `tests/test_client.py` (new cases) | ~40 |
| `client` e2e | `tests/test_client_e2e.py` (new file) | ~20 |

Coverage: unsafe zip / symlinks / zip bomb / frontmatter / duplicate / extension / macOS filtering / normalization / dedup / traversal / listing / deletion / agent invalidation / upload lifecycle / thread isolation / URL encoding / config pollution.
