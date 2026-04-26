# Automation Index

23 launchd plists (zero-token background tasks). All labels prefixed `com.enriquezOS.`.

> **Times in PHT** (Allen's local timezone). launchd uses local time.
> **Logs** land in `.tmp/<name>-error.log` (gitignored, regenerated each run).
> **Manage:** `launchctl bootstrap gui/$UID <plist>` to load, `launchctl bootout` to unload, `launchctl start <Label>` to fire now.

## Daily — morning batch

| Time | Plist | Script | Purpose |
|---|---|---|---|
| 05:30 | `morning-briefing` | `run_morning_briefing.sh` | Daily brief — pipeline + content buffer + outreach pace |
| 05:45 | `ai-learning-brief` | `run_ai_learning_brief.sh` | AI-curated learning summary |
| 06:00 | `memory-audit` | `tools/shared/memory_audit.py` | Memory consistency check |
| 06:00 | `tokenaudit` | `run_daily_token_audit.sh` | OAuth token expiry check across services |
| 06:00 | `tender-batch` | `tools/eps/tender_batch.py` | EPS tender pipeline run (EstimateOne ingest + analysis) |
| 06:00 | `ph-outreach-daily` | `run_ph_outreach_daily.sh` | PH outreach send batch |
| 06:30 | `jibble-clockin` | `tools/eps/jibble.sh clock-in` | EPS time tracking auto clock-in |
| 07:00 | `creator-feed` | `run_creator_feed.sh` | Refresh content-hub creator feed |
| 07:30 | `briefing-action-loop` | `run_briefing_action_loop.sh` | Surfaces overnight action items |

## Daily — afternoon / evening

| Time | Plist | Script | Purpose |
|---|---|---|---|
| 15:00 | `automation-status` | `tools/shared/automation_status.py` | Health check on all other plists |
| 17:00 | `eod-ops` | chained `eod_ops_manager.py + crm_sync.py + check_outcomes.py` | EPS end-of-day batch |
| 00:30 | `personal-crm-cleanup` | `run_personal_crm_cleanup.sh` | Personal Kanban CRM cleanup |

## Outreach + Ad cron jobs

| Time | Plist | Script | Purpose |
|---|---|---|---|
| 09:00 AM PH | `outreach-skool` | `tools/personal/outreach_coach.py discover --source skool --limit 10` | Discover Skool community coaches |
| 09:30 AM PH | `outreach-ig` | `tools/personal/outreach_coach.py discover --source ig --limit 15` | Discover Instagram profiles |
| 10:00 AM PH | `outreach-linkedin` | `tools/personal/outreach_coach.py discover --source linkedin --limit 5` | Discover LinkedIn prospects |
| Every 30 min | `outreach-enrich` | `tools/personal/outreach_coach.py enrich --limit 20` | Enrich discovered prospects |
| 02:00 AM PH | `ad-iterator` | `tools/personal/ad_iterator.py --once` | Daily ad spend iterator |

**Setup:**
```bash
# Symlink each plist to ~/Library/LaunchAgents/
ln -s "$(pwd)/com.enriquezOS.outreach-skool.plist" ~/Library/LaunchAgents/
ln -s "$(pwd)/com.enriquezOS.outreach-ig.plist" ~/Library/LaunchAgents/
ln -s "$(pwd)/com.enriquezOS.outreach-linkedin.plist" ~/Library/LaunchAgents/
ln -s "$(pwd)/com.enriquezOS.outreach-enrich.plist" ~/Library/LaunchAgents/
ln -s "$(pwd)/com.enriquezOS.ad-iterator.plist" ~/Library/LaunchAgents/

# Load all 5
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.enriquezOS.outreach-skool.plist
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.enriquezOS.outreach-ig.plist
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.enriquezOS.outreach-linkedin.plist
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.enriquezOS.outreach-enrich.plist
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.enriquezOS.ad-iterator.plist
```

## Polling intervals

| Interval | Plist | Script | Purpose |
|---|---|---|---|
| 10 min | `crm-sync` | `tools/eps/crm_sync.py` | Pipedrive ↔ SM8 sync |
| 15 min | `inbox-sync` | `run_inbox_sync.sh` | content-hub inbox + comments/DMs |
| 10 min | `n8n-monitor` | `run_n8n_monitor.sh` | **LEGACY — flag for removal**, n8n superseded by Claude Code agent system |

## Weekly

| Schedule | Plist | Script | Purpose |
|---|---|---|---|
| Mon 06:30 | `ig-token-refresh` | `run_ig_token_refresh.sh` | Refresh Instagram user token before ~60d expiry |
| Mon 07:00 | `reengage-campaign` | `tools/eps/reengage_campaign.py --mode all` | EPS re-engagement email campaign |
| Sun 03:00 | `ph-outreach-discover` | `run_ph_outreach_discover.sh` | PH outreach lead discovery (FB groups → enrich) |
| Sun 08:00 | `ryan-self-improve` | `run_ryan_self_improve.sh` | Ryan client labeler self-improvement loop |

## Always-on (RunAtLoad, no schedule)

| Plist | Script | Purpose |
|---|---|---|
| `crm-kanban` | `python3 tools/crm_kanban/app.py` | Personal Kanban CRM at http://localhost:5001 |
| `dashboard` | gunicorn `tools/dashboard/app:app` | Internal dashboard |
| `eps-dashboard` | `tools/eps-dashboard/app.py` | EPS dashboard ⚠️ **broken path** — plist points at `/Users/allenenriquez/Desktop/Allen Enriquez/` (stale, repo moved to `~/Developer/`). Fix before next bootstrap. |
| `whatsapp-webhook` | `tools/eps/whatsapp_start.sh` | EPS WhatsApp incoming-message webhook |

## Known issues

- **`n8n-monitor` is legacy.** Allen moved off n8n in April 2026 (memory: `project_enriquez_os_direction.md`, content strategy `apr2026`). Polls every 10 min for nothing. Candidate for `launchctl bootout` + plist deletion.
- **`eps-dashboard` plist has a stale Desktop path.** Fails silently — service never starts. Update `ProgramArguments` to `/Users/allenenriquez/Developer/Allen-Enriquez/tools/eps-dashboard/`.
- **No central health log.** `automation-status` plist runs at 15:00 PHT and writes to `.tmp/automation-status-error.log` — but failures of OTHER plists are not aggregated anywhere visible. Consider routing `.tmp/*-error.log` summary into the daily morning brief.
- **Failure mode is silent.** launchd logs to `.tmp/<name>-error.log`. If a script throws, the file fills up; no alert reaches Allen unless the morning brief surfaces it.

## How to add a new plist

1. Create `automation/com.enriquezOS.<name>.plist` with `Label`, `ProgramArguments`, schedule (`StartCalendarInterval` or `StartInterval`), `StandardErrorPath` (`.tmp/<name>-error.log`), `StandardOutPath`.
2. Symlink to `~/Library/LaunchAgents/`: `ln -s "$(pwd)/com.enriquezOS.<name>.plist" ~/Library/LaunchAgents/`. **Verify the link** — some plists in the repo are standalone copies, not symlinks (memory: `feedback_launchd_plist_symlinks.md`).
3. `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.enriquezOS.<name>.plist`
4. Add a row to this README. Same row, same shape.
5. Verify it fires: `launchctl start com.enriquezOS.<name>` then `tail -f .tmp/<name>-error.log`.

## Related

- Status checker: `tools/shared/automation_status.py` — runs at 15:00 PHT, last-run scan.
- Memory: `feedback_launchd_plist_symlinks.md` — verify symlink before editing plists; some are standalone copies.
- Memory: `feedback_restructure_base_dir.md` — `Path(__file__).parent.parent` breaks silently when scripts move; bash wrappers in this folder mostly use absolute paths to `Allen-Enriquez/`.
