#!/usr/bin/env bash
# Helper: prints Railway env vars to paste into Railway dashboard.
#
# Usage:
#   ./deploy-railway.sh              # prints values
#   ./deploy-railway.sh --set        # uses railway CLI to set them directly
#
# Prereqs before --set:
#   1. npm i -g @railway/cli
#   2. railway login
#   3. railway link   (from this dir, after railway init)

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

RYAN_TOKEN="$REPO_ROOT/projects/personal/clients/ryan/token_ryan.pickle"
ALLEN_AI_TOKEN="$REPO_ROOT/projects/personal/token_personal_ai.pickle"
ENV_FILE="$REPO_ROOT/projects/.env"

if [ ! -f "$RYAN_TOKEN" ]; then
  echo "ERROR: missing $RYAN_TOKEN" >&2
  exit 1
fi
if [ ! -f "$ALLEN_AI_TOKEN" ]; then
  echo "ERROR: missing $ALLEN_AI_TOKEN" >&2
  exit 1
fi

# Extract Anthropic key from shared projects/.env or shell env
ANTHROPIC_KEY="$(grep -E '^ANTHROPIC_API_KEY=' "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")"
if [ -z "$ANTHROPIC_KEY" ]; then
  ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"
fi
if [ -z "$ANTHROPIC_KEY" ]; then
  echo "ERROR: ANTHROPIC_API_KEY not found in any .env" >&2
  exit 1
fi

RYAN_B64="$(base64 < "$RYAN_TOKEN" | tr -d '\n')"
ALLEN_B64="$(base64 < "$ALLEN_AI_TOKEN" | tr -d '\n')"

if [ "${1:-}" = "--set" ]; then
  if ! command -v railway >/dev/null 2>&1; then
    echo "ERROR: railway CLI not installed. Run: npm i -g @railway/cli" >&2
    exit 1
  fi
  railway variables --set "ANTHROPIC_API_KEY=$ANTHROPIC_KEY"
  railway variables --set "RYAN_GMAIL_TOKEN=$RYAN_B64"
  railway variables --set "ALLEN_AI_GMAIL_TOKEN=$ALLEN_B64"
  echo
  echo "Env vars set. Deploy with: railway up"
  exit 0
fi

echo "# Paste these into Railway dashboard → Service → Variables → Raw Editor"
echo "# (or run: ./deploy-railway.sh --set   with railway CLI installed + linked)"
echo
echo "ANTHROPIC_API_KEY=$ANTHROPIC_KEY"
echo "RYAN_GMAIL_TOKEN=$RYAN_B64"
echo "ALLEN_AI_GMAIL_TOKEN=$ALLEN_B64"
