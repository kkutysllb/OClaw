# Auth Module Test Plan

## Test Matrix

| Mode | Start Command | Auth Layer | Port |
|------|---------|---------|------|
| Standard Mode | `make dev` | Gateway AuthMiddleware + LangGraph auth | 2026 (nginx) |
| Gateway Mode | `make dev-pro` | Gateway AuthMiddleware (full) | 2026 (nginx) |
| Direct Gateway | `cd backend && make gateway` | Gateway AuthMiddleware | 8001 |
| Direct LangGraph | `cd backend && make dev` | LangGraph auth | 2024 |

All tests below must be executed in each mode.

---

## Section 1: Environment Prep

### 1.1 First Startup (Clean Database)

```bash
rm -f backend/.kkoclaw/users.db
make dev          # or make dev-pro
```

**Verification:**
- Console outputs admin email and random password
- Password format: 22-char `secrets.token_urlsafe(16)` string
- Email: `admin@kkoclaw.dev`
- Prompt: `Change it after login: Settings -> Account`

### 1.2 Non-First Startup

```bash
make dev  # without clearing database
```

**Verification:** Console does not output password. If admin still `needs_setup=True`, warning is shown.

### 1.3 Environment Variables

| Variable | Verification |
|------|------|
| `AUTH_JWT_SECRET` not set | Warning on startup, auto-generates ephemeral key |
| `AUTH_JWT_SECRET` set | No warning, sessions survive restart |

---

## Section 2: API Flow Tests

> Use `BASE=http://localhost:2026` for standard and Gateway modes. Use corresponding port for direct connection.
> **CSRF token extraction**: `CSRF=$(grep csrf_token cookies.txt | awk '{print $NF}')`

### 2.1 Register + Login + Session

- **TC-API-01**: Setup status check — `GET /api/v1/auth/setup-status` → `{"needs_setup": false}`
- **TC-API-02**: Admin first login — `POST /api/v1/auth/login/local` → 200, cookies contain `access_token` (HttpOnly) + `csrf_token`
- **TC-API-03**: Get current user — `GET /api/v1/auth/me` → `{"email": "admin@kkoclaw.dev", "system_role": "admin", "needs_setup": true}`
- **TC-API-04**: Setup flow (change email + password) — `POST /api/v1/auth/change-password` → 200, email updated, `needs_setup` becomes `false`
- **TC-API-05**: Regular user registration — `POST /api/v1/auth/register` → 201, `system_role` is `"user"`, auto-login
- **TC-API-06**: Logout — `POST /api/v1/auth/logout` → 200, subsequent access returns 401

### 2.2 Multi-Tenant Isolation

- **TC-API-07**: User A creates thread → successful
- **TC-API-08**: User B cannot access User A's thread → 404 (not 403, avoids leaking thread existence)
- **TC-API-09**: User B searching threads doesn't see User A's → returns 0 or only User B's threads

### 2.3 Standard Mode LangGraph Server Isolation

- **TC-API-10**: LangGraph endpoints require cookie → 401 without cookie
- **TC-API-11**: LangGraph accessible with cookie → 200, returns user's threads
- **TC-API-12**: LangGraph isolation — users only see their own threads

### 2.4 Token Invalidation

- **TC-API-13**: Old token invalidated after password change → 401 (token_version mismatch)
- **TC-API-14**: New cookie works after password change → 200

### 2.5 Error Response Format

- **TC-API-15**: Structured error response — `{"code": "invalid_credentials", "message": "Incorrect email or password"}`
- **TC-API-16**: Duplicate email registration → 400, `{"code": "email_already_exists", ...}`

---

## Section 3: Attack Tests

### 3.1 Brute Force Protection

- **TC-ATK-01**: IP rate limiting — 5 failed attempts → 401 each, 6th → 429 `"Too many login attempts"`
- **TC-ATK-02**: Correct password also rejected after rate limit triggered → 429 (5-min lockout)
- **TC-ATK-03**: Successful login clears rate limit → 200, counter reset

### 3.2 CSRF Protection

- **TC-ATK-04**: POST without CSRF token → 403 `"CSRF token missing"`
- **TC-ATK-05**: Wrong CSRF token → 403 `"CSRF token mismatch"`

### 3.3 Cookie Security

- **TC-ATK-06**: HTTP mode cookie attributes — `access_token`: `HttpOnly; Path=/; SameSite=lax` (no Secure, no Max-Age); `csrf_token`: `Path=/; SameSite=strict` (no HttpOnly)
- **TC-ATK-07**: HTTPS mode cookie attributes — `access_token`: `Secure` added, `Max-Age=604800`; `csrf_token`: `Secure` added
- **TC-ATK-07a**: HTTP/HTTPS comparison table

| Attribute | HTTP access_token | HTTPS access_token | HTTP csrf_token | HTTPS csrf_token |
|------|------|------|------|------|
| HttpOnly | Yes | Yes | No | No |
| Secure | No | **Yes** | No | **Yes** |
| SameSite | Lax | Lax | Strict | Strict |
| Max-Age | None (session cookie) | **604800** (7 days) | None | None |

### 3.4 Unauthorized Access

- **TC-ATK-08**: No cookie access to protected endpoints → all return 401
- **TC-ATK-09**: Forged JWT → 401 (signature verification fails)
- **TC-ATK-10**: Expired JWT → 401

### 3.5 Password Security

- **TC-ATK-11**: Insufficient password length → 422 (min_length=8)
- **TC-ATK-12**: Passwords not stored in plaintext → `password_hash` starts with `$2b$` (bcrypt)

---

## Section 4: UI Operation Tests

### 4.1 First Login Flow

- **TC-UI-01**: Access homepage redirects to login → `/workspace` → `/login`
- **TC-UI-02**: Login page — admin login → redirects to `/setup` (`needs_setup=true`)
- **TC-UI-03**: Setup page — complete setup → redirects to `/workspace`, refresh stays
- **TC-UI-04**: Setup password mismatch → shows "Passwords do not match" error

### 4.2 Daily Use

- **TC-UI-05**: Create conversation → left sidebar shows new thread
- **TC-UI-06**: Conversation persistence → survives page refresh
- **TC-UI-07**: Logout → redirects to `/`, direct `/workspace` access → redirects to `/login`

### 4.3 Multi-User Isolation

- **TC-UI-08**: User A can't see User B's conversations → empty workspace
- **TC-UI-09**: Direct URL access to other user's thread → 404 or blank page

### 4.4 Session Management

- **TC-UI-10**: Tab switch session check → silent check, no 401 spam
- **TC-UI-11**: Session expired after tab switch → auto-redirect to `/login`
- **TC-UI-12**: Change password in Settings → success, no re-login needed

### 4.5 Registration Flow

- **TC-UI-13**: Register from login page → auto-redirect to `/workspace`
- **TC-UI-14**: Duplicate email → "Email already registered" error

### 4.6 Password Reset (CLI)

- **TC-UI-15**: `reset_admin` → new password, redirects to `/setup` page, old sessions invalidated

---

## Section 5: Upgrade Tests

Tests simulating upgrade from no-auth to auth version:

- **TC-UPG-01**: First startup creates admin with random password
- **TC-UPG-02**: Old threads migrated to admin → count preserved, `owner_id` set
- **TC-UPG-03**: Old thread content intact → `metadata.title` preserved
- **TC-UPG-04**: New users can't see old threads → returns 0
- **TC-UPG-05**: `users.db` auto-created with `needs_setup`, `token_version` columns
- **TC-UPG-06**: `users.db` uses WAL mode
- **TC-UPG-07**: Legacy `.env` without `AUTH_JWT_SECRET` → warning but works, sessions lost on restart
- **TC-UPG-08**: Old `config.yaml` without auth section → no impact
- **TC-UPG-09**: Old frontend cache → intercepted by AuthMiddleware (401), reloads
- **TC-UPG-10**: Bookmarked URLs → redirects to `/login` with `?next=` param
- **TC-UPG-11**: Rollback to main branch → works, old data accessible
- **TC-UPG-12**: Re-upgrade to auth branch → existing `users.db` recognized, old admin still usable
- **TC-UPG-13**: Restart resets password for un-setup admin → new password printed, old invalid
- **TC-UPG-14**: Password lost → restart to get new password (no CLI needed)
- **TC-UPG-15**: Normal user registration while admin is dormant → successful, role is `user`
- **TC-UPG-16**: Dormant admin doesn't affect normal operations → normal user works fine
- **TC-UPG-17**: Dormant admin eventually completes setup → email updated, `needs_setup=false`
- **TC-UPG-18**: JWT key rotation → old password still works (in DB), old JWTs invalidated

---

## Section 6: Reentrancy Tests

### 6.1 Startup Reentrancy

- **TC-REENT-01**: Consecutive restarts don't create duplicate admins → count stays 1
- **TC-REENT-02**: Concurrent multi-process startup → no error, only 1 admin (SQLite UNIQUE constraint)
- **TC-REENT-03**: Thread migration idempotent → second call has `migrated = 0`

### 6.2 Login Reentrancy

- **TC-REENT-04**: Repeated logins get new cookies → all 3 cookies valid (multi-session)
- **TC-REENT-05**: Login-logout-login → no state residue

### 6.3 Password Change Reentrancy

- **TC-REENT-06**: Two consecutive password changes → both succeed, `token_version` incremented by 2
- **TC-REENT-07**: Old cookies invalidated after password change → only latest cookie valid

### 6.4 Registration Reentrancy

- **TC-REENT-08**: Concurrent registration with same email → one 201, one 400, DB has 1 record

### 6.5 Rate Limiter Reentrancy

- **TC-REENT-09**: Rate limit expires, counter resets → new attempts start from 0
- **TC-REENT-10**: Successful login resets counter → subsequent failures count from 0

### 6.6 CSRF Token Reentrancy

- **TC-REENT-11**: Same CSRF token used multiple times → all succeed (Double Submit Cookie, not one-time nonce)

### 6.7 Thread Operation Reentrancy

- **TC-REENT-12**: Double delete same thread → 200 or 404, never 500

### 6.8 `reset_admin` Reentrancy

- **TC-REENT-13**: Two consecutive `reset_admin` calls → P1 ≠ P2, only P2 works, `token_version` +2

### 6.9 Setup Flow Reentrancy

- **TC-REENT-14**: Access `/setup` after completing setup → redirects to `/workspace`
- **TC-REENT-15**: Refresh mid-setup → stays on `/setup`, form clears without error

---

## Section 7: Mode Difference Tests

### 7.1 Standard Mode Specific

- **TC-MODE-01**: LangGraph Server requires cookie → 403 without
- **TC-MODE-02**: LangGraph auth `token_version` check → old cookie → 403, new cookie → 200
- **TC-MODE-03**: LangGraph auth owner filter isolation

### 7.2 Gateway Mode Specific

- **TC-MODE-04**: All requests go through AuthMiddleware → LangGraph Server not running
- **TC-MODE-05**: Full auth flow in Gateway mode → thread CRUD with embedded runtime, CSRF protection

### 7.3 Direct Gateway (No Nginx)

- **TC-GW-01**: AuthMiddleware protects all non-public routes → all return 401
- **TC-GW-02**: Public routes don't need cookie → 200/405/422 but not 401
- **TC-GW-03**: Full register + login + CSRF flow
- **TC-GW-04**: Rate limiter with real IP (not `X-Real-IP`)
- **TC-GW-05**: `X-Real-IP` spoofing ineffective on direct connection

### 7.4 Docker Deployment

- **TC-DOCKER-01**: `users.db` persisted via volume → visible on host
- **TC-DOCKER-02**: Session survives container restart (with `AUTH_JWT_SECRET`)
- **TC-DOCKER-03**: Multi-worker rate limiter independent (known limitation: in-process dict not shared)
- **TC-DOCKER-04**: IM channels bypass auth → no auth errors in logs
- **TC-DOCKER-05**: Admin credentials written to 0600 file (not logged) → `admin_initial_credentials.txt` mode 0600
- **TC-DOCKER-06**: Gateway-mode Docker deployment → no langgraph container, auth flow normal

### 7.5 Edge Cases

- **TC-EDGE-01**: Valid-format but random JWT → `{"code": "token_invalid", "message": "Token error: invalid_signature"}`
- **TC-EDGE-02**: Registration with `system_role=admin` → returns `"user"` (field ignored)
- **TC-EDGE-03**: Concurrent password changes → one 200, one 400
- **TC-EDGE-04**: Cookie SameSite verification → `access_token: SameSite=lax`, `csrf_token: SameSite=strict`
- **TC-EDGE-05**: HTTP no Max-Age, HTTPS has Max-Age=604800
- **TC-EDGE-06**: Public path trailing slash → 307 or 200/405, never 401

### 7.6 Red Team Adversarial Tests

- **Path Confusion Bypass**: Encoded/double-slash/path traversal attempts → all 401 or 404
- **CSRF Adversarial Matrix**: 4 cases (no header, no cookie, mismatch, old token) → all 403
- **Token Replay**: Logout doesn't bump `token_version` → old token still valid until expiry (known limitation)
- **Cross-Site Forced Logout**: `POST /logout` without auth → 200 (low risk: SameSite=Lax limits real cross-site impact)
- **Metadata Injection**: Injected `owner_id` in request → overwritten by server with actual user ID
- **HTTP Method Probing**: HEAD/OPTIONS → 401 or 405, TRACE → 405
- **Rate Limiter IP Bypass**: `X-Forwarded-For` spoofing → ineffective, rate limiter uses `client.host`
- **Junk Cookie Penetration**: Junk cookie passes middleware presence check but fails `@require_auth` JWT validation → 401

---

## Section 8: Regression Checklist

Must pass after any auth-related code change:

```bash
# Unit tests (168 tests)
cd backend && PYTHONPATH=. uv run pytest \
  tests/test_auth.py \
  tests/test_auth_config.py \
  tests/test_auth_errors.py \
  tests/test_auth_type_system.py \
  tests/test_auth_middleware.py \
  tests/test_langgraph_auth.py \
  -v

# Core endpoint smoke tests
curl -s $BASE/health                              # 200
curl -s $BASE/api/models                          # 401 (no cookie)
curl -s -X POST $BASE/api/v1/auth/setup-status    # 200
curl -s $BASE/api/v1/auth/me -b cookies.txt       # 200 (with cookie)
```
