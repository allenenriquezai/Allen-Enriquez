# SOP: Debugging Web & Mobile App Failures

**When to use:** deploy failures, runtime crashes, hung builds, "it worked yesterday" bugs on web/mobile apps (Railway, Vercel, Fly, Expo, App Store, etc.).

**Core principle:** Diagnose before you fix. One wrong assumption costs an hour. Always confirm which **layer** is broken before touching code.

---

## Phase 1 — Classify the Failure (≤5 min)

Before anything else, answer: **which phase died?** Don't skip this. Don't trust handoff notes.

### Universal build/deploy phases

| Phase | What it means | Common cause |
|---|---|---|
| `SNAPSHOT_CODE` | Git pull / tarball upload | Large files, gitignore wrong, repo access |
| `BUILD_IMAGE` | Docker build / nixpacks / npm build | Code errors, missing deps, bad env at build, DB queries at build time |
| `PUBLISH_IMAGE` | Push to registry | Network, registry auth, disk quota |
| `CREATE_CONTAINER` | Allocate resources | Resource limits, plan quotas |
| `MIGRATE_VOLUMES` | Mount volumes | Volume locks, region mismatch |
| `PRE_DEPLOY_COMMAND` | Startup script | Script errors, missing env at runtime |
| `WAIT_FOR_DEPENDENCIES` | Linked services up | Service discovery, DNS |
| `DRAIN_INSTANCES` | Stop old container | Graceful shutdown hooks, `overlapSeconds` |
| `HEALTHCHECK` | App responds 2xx | Port binding, healthcheck path wrong, slow boot |

### How to find the failed phase

**Railway:** GraphQL query — this is the single most valuable call:
```graphql
query { deploymentEvents(id: "<deployment-id>", first: 50) {
  edges { node { step createdAt completedAt payload { error } } }
} }
```
Last event with non-null `payload.error` = root cause phase.

**Vercel:** `vercel inspect <deployment-url> --logs` → look for `buildContainer:` vs `deploymentContainer:` prefix.

**Fly:** `fly logs --region <r>` + `fly status --all` → check `Status` column per machine.

**Expo/EAS:** `eas build:view <id>` → `buildPhase` field.

**App Store Connect:** processing failure type is in the email — `BinaryInvalid`, `InvalidPlatformValue`, `MissingPushNotificationEntitlement`.

---

## Phase 2 — Pull The Right Logs (≤5 min)

Once you know the phase, pull ONLY that phase's logs. Different phases = different log streams.

| Phase | Log source |
|---|---|
| Build | `buildLogs` / CI output / Docker build log |
| Deploy (container start) | `deploymentLogs` / runtime stdout |
| HTTP / request | `httpLogs` / access log |
| Healthcheck | Platform healthcheck status + app `/health` endpoint |

**Anti-pattern:** pulling runtime logs when the build failed. They'll show the OLD (healthy) container — you'll convince yourself the app is fine.

---

## Phase 3 — Classify The Root Cause

Map the actual error to a category. Each category has a known fix class.

### Build-time failures
- `no such table: X`, `cannot open file: /data/...` → **DB/volume access at build time**. Volume is NOT mounted during build. Fix: mark route `export const dynamic = 'force-dynamic'` or move query into request handler.
- `Module not found` → missing dep, bad import path, case sensitivity (Mac→Linux)
- `TypeError ... at build` → bad env var fallback, missing `NEXT_PUBLIC_*` at build
- `ENOSPC` → build cache full, disk quota
- OOM on build → reduce parallel workers, increase instance size

### Deploy-time failures
- `failed to mount volume` → volume lock (old container still attached). Fix: set `overlapSeconds=0`, force-stop old instance
- `address already in use` → port collision, PORT env wrong
- `exec format error` → arch mismatch (arm64 vs amd64 Docker image)

### Runtime crashes
- `EADDRINUSE`, `EACCES` on port → permissions / port binding
- Fast crash loop → read stderr on first boot, not tail
- Memory crashes → profile heap, trim deps, bump plan

### Healthcheck failures
- 404 on healthcheck path → path wrong in `railway.json`/`fly.toml`
- Slow boot → extend `healthcheckTimeout`
- 5xx healthcheck → app boots but init fails downstream (DB, env, etc.)

### Mobile-specific
- iOS: `ITMS-90xxx` codes are googleable verbatim
- Android: `AAB` upload rejection → signing mismatch / versionCode collision
- Expo: `Provisioning profile invalid` → EAS credentials rotation

---

## Phase 4 — Fix & Verify

1. **Smallest possible fix.** Revert-friendly.
2. **Commit message names the failure class + fix.** Example: `fix(content-hub): remove build-breaking DELETE in db init`.
3. **Watch the next deploy end-to-end.** Poll until terminal status (SUCCESS / FAILED / CRASHED). Don't assume.
4. **Hit the live endpoint.** `curl -sI` + follow redirects. 2xx = real verification.
5. **Tail logs for 60s after success.** New deploys sometimes crash 30s in.

---

## Hard Rules

1. **Never trust handoff notes verbatim.** Re-classify failure phase first. Prior session may have been wrong.
2. **One GraphQL event query beats an hour of guessing.** Always check `deploymentEvents` before logs.
3. **Volume lock is a last resort hypothesis, not a first.** It's rare. Most "deploy failures" are actually build failures.
4. **If build succeeds but deploy fails on first boot:** read runtime logs from START, not tail. Crashes appear in first 5 seconds.
5. **Don't fix what you can't reproduce.** If can't repro locally, add logging + redeploy before guessing.
6. **Memory: save the failure pattern, not the fix.** Fixes rot. Patterns recur.

---

## Quick Reference — Railway Diagnostic Chain

Run in order, stop at first meaningful signal:

```bash
# 1. Which deployments failed?
curl -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ deployments(first:5, input:{projectId:\"PID\", environmentId:\"EID\", serviceId:\"SID\"}) { edges { node { id status createdAt } } } }"}'

# 2. Which phase died on deployment X?
curl -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ deploymentEvents(id:\"DID\", first:50) { edges { node { step payload { error } } } } }"}'

# 3. Pull logs for THAT phase only
# Build → buildLogs(deploymentId)
# Deploy/runtime → deploymentLogs(deploymentId)
# HTTP → httpLogs(deploymentId)
```

Token at `~/.railway/config.json` → `accessToken` field.

---

## When This SOP Fails

If you've been debugging >30 min and haven't narrowed the phase + root cause: **stop, write down the last 3 hypotheses you tried, and open this SOP from the top.** Fresh pass usually catches the skipped step.
