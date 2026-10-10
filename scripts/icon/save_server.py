"""Tiny local helper: the icon page POSTs a rendered PNG here and it is written into public/icons."""
import http.server, sys
from pathlib import Path
OUT = Path(sys.argv[1])
class H(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Access-Control-Allow-Methods', 'POST'); self.send_header('Access-Control-Allow-Headers', '*'); self.end_headers()
    def do_POST(self):
        name = Path(self.path.strip('/')).name
        if not name.endswith('.png'):
            self.send_response(400); self.end_headers(); return
        data = self.rfile.read(int(self.headers['Content-Length']))
        (OUT / name).write_bytes(data)
        self.send_response(200); self.send_header('Access-Control-Allow-Origin', '*'); self.end_headers(); self.wfile.write(f'saved {name} {len(data)}'.encode())
http.server.HTTPServer(('127.0.0.1', 8766), H).serve_forever()
