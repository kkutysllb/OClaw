# OClaw Desktop Release Process

This document explains how to build, sign, notarize, and publish the OClaw desktop app (`desktop-electron/`) to GitHub Release via GitHub Actions, with `electron-updater` for automatic client updates.

## Overall Process

```
Maintainer tags → GitHub Actions → electron-builder → Apple Notary Service
    │                  │                    │                    │
    │ git tag v0.x.0   │                    │                    │
    ├─────────────────▶│ 1. Checkout code   │                    │
    │   git push --tags│ 2. pnpm install    │                    │
    │                  │ 3. uv install      │                    │
    │                  │    Python 3.12     │                    │
    │                  │ 4. PyInstaller     │                    │
    │                  │    oclaw-gateway   │                    │
    │                  │ 5. tsc compile main│                    │
    │                  │ 6. electron-builder│──sign──▶            │
    │                  │    .app + .dmg     │──notarize──▶──────▶ │
    │                  │    Notary + Staple │    notarize        │
    │                  │◀───ticket──────────┤                    │
    │                  │ 7. --publish always│                    │
    │                  │    Upload to GitHub│                    │
    │                  │    Release + write │                    │
    │                  │    latest-*.yml    │                    │
    │                  ▼                    │                    │
    │       GitHub Release (draft)          │                    │
    │       with dmg/zip/exe/deb/rpm        │                    │
    │       + *.blockmap                     │                    │
    │       + latest-mac.yml                 │                    │
    │       + latest-linux.yml               │                    │
    │       + latest.yml                     │                    │
    │                                        │                    │
    │  Maintainer clicks "Publish release"   │                    │
    │                                        │                    │
    │        End Users                       │                    │
    │          │                             │                    │
    │          │ Launch desktop app          │                    │
    │          ▼                             │                    │
    │  electron-updater reads latest-*.yml   │                    │
    │  Found new version → update dialog     │                    │
    │  User clicks "Update Now" → download   │                    │
    │  blockmap integrity check → install    │                    │
```

## Required GitHub Secrets

| Secret Name | Value | Description | Required |
|----------|------|------|:----:|
| `MACOS_CERT_P12_BASE64` | Base64-encoded Developer ID Application `.p12` file | macOS code signing certificate | ✅ |
| `MACOS_CERT_PASSWORD` | Export password for `.p12` file | Certificate private key password | ✅ |
| `APPLE_ID` | Apple ID email | Apple Developer account | ✅ |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password | Used for `notarytool` submission | ✅ |
| `APPLE_TEAM_ID` | 10-character Apple Developer Team ID | Identifies developer team | ✅ |
| `WINDOWS_CERT_PFX_BASE64` | Base64-encoded `.pfx`/`p12` | Windows code signing | ❌ |
| `WINDOWS_CERT_PASSWORD` | Export password for `.pfx` file | Windows cert private key password | ❌ |

> ✅ = required for macOS package release; ❌ = only needed if Windows signing is desired.

## Preparing macOS Signing Certificate

### 1. Apply for Certificate in Apple Developer Portal

1. Open <https://developer.apple.com/account/resources/certificates/list>
2. Click `+` to create a new certificate, select **Developer ID Application**
3. Generate CSR locally (Keychain Access or `openssl`)
4. Upload CSR, download the generated `.cer`, double-click to install in Keychain Access

### 2. Export `.p12` File

```bash
# Keychain Access → Login → My Certificates
# Find "Developer ID Application: <Your Name> (<TeamID>)"
# Right-click → Export → Save as .p12 with a strong password
```

### 3. Base64 Encode and Upload to GitHub

```bash
base64 -i /path/to/DeveloperID.p12 | pbcopy
# Then add to GitHub repo → Settings → Secrets
# Name: MACOS_CERT_P12_BASE64
```

### 4. Generate App-Specific Password

1. Open <https://appleid.apple.com/account/manage>
2. Sign in → App-Specific Passwords → `+` generate a new password
3. Add to GitHub Secrets: `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`

## Pre-Release Self-Check

Before `git tag && git push --tags`, run these 6 local checks:

```bash
# 1. package.json version updated and not conflicting
grep '"version"' desktop-electron/package.json

# 2. macOS code signing certificate in Keychain
security find-identity -p codesigning -v

# 3. Apple Developer credentials readable locally (simulate GitHub Secrets env)
export MACOS_CERT_P12_BASE64="$(base64 -i ~/DeveloperID.p12 | tr -d '\n')"
export MACOS_CERT_PASSWORD="your p12 password"
export APPLE_ID="your@email.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="DHV5D72JNF"

# 4. .p12 base64 decodes to valid PKCS#12 (magic bytes 0x30 0x82)
echo "$MACOS_CERT_P12_BASE64" | base64 -d | head -c 4 | xxd

# 5. .p12 private key unlocks (confirm password correct)
echo "$MACOS_CERT_P12_BASE64" | base64 -d | \
  openssl pkcs12 -info -nokeys -passin "pass:$MACOS_CERT_PASSWORD" 2>&1 | head -10

# 6. Clean build (no publish, verify pipeline works)
rm -rf desktop-electron/release desktop-electron/dist
rm -rf desktop-electron/resources/gateway/*
pnpm --dir desktop-electron run build:app
```

Only push tag after all 6 steps pass.

## How to Trigger a Release

1. **Update `version` in `desktop-electron/package.json`** (no `v` prefix)

2. **Commit and tag**:
   ```bash
   git add desktop-electron/package.json
   git commit -m "chore(desktop): bump version to 0.1.1"
   git tag v0.1.1
   git push origin main --tags
   ```

3. **GitHub Actions auto-starts**: 3 matrix jobs run in parallel:
   - `macOS (arm64)` — sign + notarize + produce `.dmg` + `.zip`
   - `Linux (deb + rpm)` — produce `.deb` + `.rpm`
   - `Windows (NSIS)` — produce `.exe` + blockmap

4. **Release auto-created as draft**: electron-builder uploads artifacts + `latest-*.yml` manifests.

5. **Manual review and publish**: Verify all platform artifacts, spot-test `.dmg`, click **Publish release**.

## electron-updater Auto-Update

Desktop app code (`desktop-electron/src/updater.ts`) calls `autoUpdater.checkForUpdates()` 5 seconds after `app.whenReady()`:

- `autoUpdater` reads the `publish` section from `package.json`
- Fetches `latest-*.yml` from the latest release
- If the YAML version > current app version → shows native update dialog
- User clicks "Update Now" → background download with differential download + SHA512 verification via `*.blockmap`
- Notarized macOS packages skip Gatekeeper; unsigned ones show "unidentified developer" warning

> Users need no extra configuration. As long as the published Release is public (not draft), all installed desktop apps will see an update prompt after 5 seconds.

## Local Verification

### Quick smoke test (TS compile only):
```bash
cd desktop-electron && pnpm run build
```

### Full build (PyInstaller + frontend + electron-builder, no publish):
```bash
cd desktop-electron && pnpm run build:app
```

### Local sign + notarize (no publish):
```bash
export CSC_LINK="$(cat ~/DeveloperID.p12 | base64 | tr -d '\n')"
export CSC_KEY_PASSWORD="your p12 password"
export APPLE_ID="your@email.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="DHV5D72JNF"
cd desktop-electron && pnpm exec electron-builder --mac --arm64 --publish never
```

### Clean rebuild:
```bash
cd desktop-electron && rm -rf release dist && rm -rf resources/gateway/* && pnpm run build:app
```

## Common Issues

### macOS notarization fails
- Verify `MACOS_CERT_P12_BASE64` is complete
- Confirm certificate type is **Developer ID Application**
- Verify `CSC_KEY_PASSWORD` is the `.p12` export password

### macOS authentication fails
- `APPLE_APP_SPECIFIC_PASSWORD` must be an app-specific password, not the Apple ID login password
- Re-generate the app-specific password if needed

### electron-builder upload 403/404
- Confirm `GITHUB_TOKEN` has `contents: write` permission
- Verify `electron-builder.yml` owner/repo matches

### Windows SmartScreen warning
- Without Windows code signing cert, Windows shows "Windows protected your PC"
- Users need to click `More info` → `Run anyway`
- Solution: apply for EV code signing certificate

## Toolchain Versions

| Component | Version |
|------|------|
| Node.js | 22+ |
| pnpm | 10+ |
| Python | 3.12 (fixed) |
| uv | latest |
| Electron | 33.x |
| electron-builder | 25.x |
| PyInstaller | 6.x |
| macOS Runner | macos-14 (arm64) |
| Linux Runner | ubuntu-22.04 |
| Windows Runner | windows-latest |
