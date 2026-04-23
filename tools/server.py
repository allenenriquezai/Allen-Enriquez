import http.server, ssl, json, base64, os, time

UPLOAD_DIR = os.path.expanduser("~/Developer/Allen-Enriquez/.tmp/recordings")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/save":
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))
            video_bytes = base64.b64decode(data["video"])
            ext = data.get("ext", "mp4")
            filename = f"teleprompter-{int(time.time())}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(video_bytes)
            print(f"Saved: {filepath} ({len(video_bytes)} bytes)")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "file": filename}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

httpd = http.server.HTTPServer(("0.0.0.0", 4443), Handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain("cert.pem", "key.pem")
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

print(f"HTTPS server on https://192.168.100.188:4443/teleprompter.html")
print(f"Recordings save to: {UPLOAD_DIR}")
httpd.serve_forever()
