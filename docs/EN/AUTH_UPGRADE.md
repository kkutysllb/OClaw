# Authentication Upgrade Guide

OClaw has a built-in authentication module. This document is for users upgrading from non-authenticated versions.

## Core Concepts

The authentication module adopts an **always-enforced** policy:

- An admin account is automatically created on first startup with a random password printed to the console log
- Authentication is enforced from the very beginning with no race window
- Historical conversations (threads created before the upgrade) are automatically migrated under the admin account

## Upgrade Steps

### 1. Update Code

```bash
git pull origin main
cd backend && make install
```

### 2. First Startup

```bash
make dev
```

The console will output:

```
============================================================
  Admin account created on first boot
  Email:    admin@kkoclaw.dev
  Password: aB3xK9mN_pQ7rT2w
  Change it after login: Settings → Account
============================================================
```

If the service restarts before you log in, don't worry — as long as setup is not complete, the password will be reset and reprinted to the console on each startup.

### 3. Login

Visit `http://localhost:2026/login` and log in with the console-output email and password.

### 4. Change Password

After logging in, go to Settings → Account → Change Password.

### 5. Add Users (Optional)

Other users register via the `/login` page and automatically receive the **user** role. Each user can only see their own conversations.

## Security Mechanisms

| Mechanism | Description |
|------|------|
| JWT HttpOnly Cookie | Token not exposed to JavaScript, preventing XSS theft |
| CSRF Double Submit Cookie | All POST/PUT/DELETE requests require `X-CSRF-Token` |
| bcrypt Password Hashing | Passwords not stored in plaintext |
| Multi-tenant Isolation | Users can only access their own threads |
| HTTPS Adaptive | Detects `x-forwarded-proto`, automatically sets `Secure` cookie flag |

## Common Operations

### Forgot Password

```bash
cd backend

# Reset admin password
python -m app.gateway.auth.reset_admin

# Reset specified user password
python -m app.gateway.auth.reset_admin --email user@example.com
```

A new random password will be output.

### Full Reset

Delete the user database and restart to automatically create a new admin:

```bash
rm -f backend/.kkoclaw/users.db
# Restart the service, new password printed to console
```

## Data Storage

| File | Content |
|------|------|
| `.kkoclaw/users.db` | SQLite user database (password hash, roles) |
| `AUTH_JWT_SECRET` in `.env` | JWT signing key (auto-generated temporary key if not set; sessions invalidated on restart) |

### Production Recommendations

```bash
# Generate a persistent JWT key to avoid all users needing to re-login after restart
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add the output to .env:
# AUTH_JWT_SECRET=<generated-key>
```

## API Endpoints

| Endpoint | Method | Description |
|------|------|------|
| `/api/v1/auth/login/local` | POST | Email/password login (OAuth2 form) |
| `/api/v1/auth/register` | POST | Register new user (user role) |
| `/api/v1/auth/logout` | POST | Logout (clear cookies) |
| `/api/v1/auth/me` | GET | Get current user info |
| `/api/v1/auth/change-password` | POST | Change password |
| `/api/v1/auth/setup-status` | GET | Check if admin exists |

## Compatibility

- **Standard mode** (`make dev`): Fully compatible, admin auto-created
- **Gateway mode** (`make dev-pro`): Fully compatible
- **Docker deployment**: Fully compatible, `.kkoclaw/users.db` requires persistent volume mount
- **IM channels** (Feishu/Slack/Telegram): Communicate via LangGraph SDK, bypassing the authentication layer
- **OClawClient** (embedded): Does not go through HTTP, unaffected by authentication

## Troubleshooting

| Symptom | Cause | Solution |
|------|------|------|
| No password shown after startup | Admin already exists (not first startup) | Use `reset_admin` to reset, or delete `users.db` |
| POST returns 403 after login | CSRF token missing | Confirm frontend has been updated |
| Need to re-login after restart | `AUTH_JWT_SECRET` not persisted | Set a fixed key in `.env` |
