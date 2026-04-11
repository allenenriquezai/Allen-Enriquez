#!/bin/bash
# Start WhatsApp webhook server + Cloudflare tunnel
# Managed by launchd: com.enriquezOS.whatsapp-webhook

BASE_DIR="/Users/allenenriquez/Desktop/Allen Enriquez"
PORT=5050

# Kill any existing processes
pkill -f "whatsapp_webhook" 2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 1

# Start webhook server
cd "$BASE_DIR"
/usr/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from tools.whatsapp_webhook import app
app.run(host='0.0.0.0', port=$PORT, debug=False)
" &
WEBHOOK_PID=$!
echo "Webhook server started (PID: $WEBHOOK_PID) on port $PORT"

# Wait for server to be ready
sleep 2

# Start Cloudflare tunnel
"$HOME/bin/cloudflared" tunnel --url "http://localhost:$PORT" &
TUNNEL_PID=$!
echo "Cloudflare tunnel started (PID: $TUNNEL_PID)"

# Wait for either process to exit
wait -n $WEBHOOK_PID $TUNNEL_PID
echo "A process exited, shutting down..."
kill $WEBHOOK_PID $TUNNEL_PID 2>/dev/null
