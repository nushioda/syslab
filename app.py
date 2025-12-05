import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "ports.json")
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")


class PortRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/ports"):
            self._send_ports()
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/ports":
            self._create_port()
            return
        self.send_error(404, "Not found")

    def do_PUT(self):
        if self.path.startswith("/api/ports/"):
            self._update_port()
            return
        self.send_error(404, "Not found")

    def do_DELETE(self):
        if self.path.startswith("/api/ports/"):
            self._delete_port()
            return
        self.send_error(404, "Not found")

    def _load_data(self):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_data(self, data):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _send_ports(self):
        ports = self._load_data()
        self._send_json({"ports": ports})

    def _create_port(self):
        body = self._read_json_body()
        if body is None:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return
        ports = self._load_data()
        new_port = {
            "id": body.get("id") or f"port-{len(ports)+1}",
            "portNumber": body.get("portNumber", ""),
            "hostname": body.get("hostname", ""),
            "vlan": body.get("vlan", ""),
            "portType": body.get("portType", "Access"),
            "lag": bool(body.get("lag", False)),
        }
        ports.append(new_port)
        self._write_data(ports)
        self._send_json(new_port, status=201)

    def _update_port(self):
        body = self._read_json_body()
        if body is None:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return
        port_id = self.path.split("/")[-1]
        ports = self._load_data()
        for port in ports:
            if port.get("id") == port_id:
                port.update({
                    "portNumber": body.get("portNumber", port.get("portNumber", "")),
                    "hostname": body.get("hostname", port.get("hostname", "")),
                    "vlan": body.get("vlan", port.get("vlan", "")),
                    "portType": body.get("portType", port.get("portType", "Access")),
                    "lag": bool(body.get("lag", port.get("lag", False))),
                })
                self._write_data(ports)
                self._send_json(port)
                return
        self._send_json({"error": "Port not found"}, status=404)

    def _delete_port(self):
        port_id = self.path.split("/")[-1]
        ports = self._load_data()
        filtered = [p for p in ports if p.get("id") != port_id]
        if len(filtered) == len(ports):
            self._send_json({"error": "Port not found"}, status=404)
            return
        self._write_data(filtered)
        self._send_json({"deleted": port_id})

    def translate_path(self, path):
        # Serve files from the public directory
        if path == "/":
            path = "/index.html"
        return os.path.join(PUBLIC_DIR, path.lstrip("/"))


def run(server_class=ThreadingHTTPServer, handler_class=PortRequestHandler):
    port = int(os.environ.get("PORT", "8000"))
    server_address = ("0.0.0.0", port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving on http://0.0.0.0:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()