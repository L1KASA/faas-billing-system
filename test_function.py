from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class HelloWorldHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "message": "Hello World from Python FaaS!",
            "path": self.path,
            "method": "GET"
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "message": "Hello World from Python FaaS!",
            "path": self.path,
            "method": "POST"
        }
        self.wfile.write(json.dumps(response).encode())


if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 80), HelloWorldHandler)
    server.serve_forever()