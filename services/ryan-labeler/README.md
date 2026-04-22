# ryan-labeler

Cloud service that auto-labels Ryan Canton's Gmail inbox (SC-Incorporated) and sends him a daily morning brief.

## Endpoints

| Method | Path | Caller | Purpose |
|---|---|---|---|
| GET  | `/health` | uptime check | liveness + last-run info |
| POST | `/label`  | n8n (Gmail Trigger → HTTP Request) | classify + label one message |
| POST | `/brief`  | Railway cron (06:30 PT daily) | send morning brief to Ryan |

## Local dev

```bash
cd services/ryan-labeler
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export CONFIG_DIR="$(pwd)/../../projects/personal/clients/ryan"
export RYAN_TOKEN_PATH="$CONFIG_DIR/token_ryan.pickle"
export ALLEN_AI_TOKEN_PATH="$(pwd)/../../projects/personal/token_personal_ai.pickle"

uvicorn main:app --reload --port 8080
```

Smoke test:

```bash
curl -sS http://localhost:8080/health | jq
curl -sS -X POST http://localhost:8080/label \
  -H 'content-type: application/json' \
  -d '{"message_id":"<real-id>","dry_run":true}' | jq
curl -sS -X POST 'http://localhost:8080/brief?dry_run=true' | jq
```

## Deploy (Railway)

One-time setup:

```bash
npm i -g @railway/cli
railway login                          # browser OAuth
cd services/ryan-labeler
railway init                           # pick "Empty Project", name: enriquez-os
railway link                           # pick service just created

./deploy-railway.sh --set              # pushes env vars (Anthropic key + 2 tokens)
railway up                             # first deploy
railway domain                         # generate public URL
```

Env vars (auto-set by `deploy-railway.sh --set`):

| Var | Source |
|---|---|
| `ANTHROPIC_API_KEY` | `projects/personal/.env` |
| `RYAN_GMAIL_TOKEN` | base64 of `projects/personal/clients/ryan/token_ryan.pickle` |
| `ALLEN_AI_GMAIL_TOKEN` | base64 of `projects/personal/token_personal_ai.pickle` |

Redeploy after code change: `railway up`.

## n8n workflow (2 nodes)

1. **Gmail Trigger** — Ryan's account credentials, poll every 1 minute, INBOX filter.
2. **HTTP Request** — `POST https://<railway-url>/label`, body `{"message_id":"{{ $json.id }}","thread_id":"{{ $json.threadId }}"}`.

## Morning brief cron (Railway)

Dashboard → service → Settings → Cron Schedule. Railway cron hits a separate command:

```
Schedule:   30 13 * * *         # 13:30 UTC = 06:30 America/Los_Angeles PDT
                                # switch to  30 14 * * *  during PST
Command:    python -c "import requests; requests.post('http://localhost:8080/brief')"
```

Simpler: use an external cron (cron-job.org free) hitting `https://<railway-url>/brief` with a shared secret header. TBD during setup.

## Known limitations (Phase 1)

- **Ephemeral filesystem:** auto-created projects and audit logs reset on redeploy. Manually add auto-created projects to `project_registry.json` + redeploy to persist. Migrate to Supabase in Phase 2.
- **Audit logs:** `/tmp` only until we wire Supabase or Railway volume.

---

## Service Improvement Backlog

Things to revisit as the service matures:

1. **Migration scripts at root** — `fix_label_*.py`, `migrate_labels.py`, `create_project_folders.py` are one-time scripts that already ran. Move to `scripts/migrations/` to keep root clean.

2. **`config/state.json` in repo** — holds runtime state (last history ID, timestamps). Will conflict on redeploy. Should live in a Railway persistent volume or lightweight DB, not version control.

3. **No tests** — a wrong routing rule silently misfiles Ryan's emails. Minimum: smoke test the classifier against 10 known sample emails (bid invite, vendor pricing, team daily, etc.) to catch prompt regressions.

4. **Service split when calendar lands** — `briefer.py` + `dashboard.py` + incoming calendar module = 3 concerns in one service. Clean split point: `ryan-labeler` (classification + routing only) vs `ryan-briefer` (summaries + calendar + app).
