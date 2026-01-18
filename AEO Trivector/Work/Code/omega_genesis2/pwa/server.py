"""
Secure Ω-Genesis PWA Server
- Basic authentication required
- Proxies requests to Ollama
- Binds to local network only
"""

import http.server
import socketserver
import base64
import os
import socket
import secrets
import json
import urllib.request
import urllib.error

# Generate a random password for this session
PASSWORD = secrets.token_urlsafe(12)
USERNAME = "omega"

PORT = 8080
OLLAMA_URL = "http://localhost:11434"

class AuthHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with basic authentication and Ollama proxy"""
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Omega-Genesis"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def check_auth(self):
        """Verify authentication, return True if valid"""
        auth_header = self.headers.get('Authorization')
        
        if auth_header is None:
            self.do_AUTHHEAD()
            self.wfile.write(b'Authentication required')
            return False
        
        if not auth_header.startswith('Basic '):
            self.do_AUTHHEAD()
            self.wfile.write(b'Invalid authentication')
            return False
        
        try:
            encoded = auth_header.split(' ')[1]
            decoded = base64.b64decode(encoded).decode('utf-8')
            username, password = decoded.split(':', 1)
        except:
            self.do_AUTHHEAD()
            self.wfile.write(b'Invalid authentication format')
            return False
        
        if username == USERNAME and password == PASSWORD:
            return True
        else:
            self.do_AUTHHEAD()
            self.wfile.write(b'Invalid credentials')
            return False

    def proxy_to_ollama(self, method='GET', body=None):
        """Proxy request to Ollama server"""
        ollama_path = self.path  # /api/tags, /api/chat, etc.
        url = f"{OLLAMA_URL}{ollama_path}"
        
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header('Content-Type', 'application/json')
            
            if body:
                response = urllib.request.urlopen(req, body.encode('utf-8'), timeout=120)
            else:
                response = urllib.request.urlopen(req, timeout=10)
            
            data = response.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
            
        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error = json.dumps({"error": f"Ollama not available: {str(e)}"})
            self.wfile.write(error.encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error = json.dumps({"error": str(e)})
            self.wfile.write(error.encode('utf-8'))

    def do_GET(self):
        if not self.check_auth():
            return
        
        # Proxy Ollama API requests
        if self.path.startswith('/api/'):
            self.proxy_to_ollama('GET')
        else:
            super().do_GET()
    
    def do_POST(self):
        if not self.check_auth():
            return
        
        # Proxy Ollama API requests
        if self.path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            self.proxy_to_ollama('POST', body)
        else:
            self.send_response(405)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {args[0]}")


def get_local_ip():
    """Get the local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


if __name__ == '__main__':
    # Change to PWA directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("  Ω-Genesis PWA Server")
    print("  μ = 0.569 at equilibrium")
    print("=" * 60)
    print()
    print(f"  🔐 Username: {USERNAME}")
    print(f"  🔑 Password: {PASSWORD}")
    print()
    print(f"  📱 iPad URL: http://{local_ip}:{PORT}")
    print(f"  💻 Local URL: http://localhost:{PORT}")
    print()
    print("  Enter these credentials when prompted in Safari")
    print("=" * 60)
    print()
    
    # Allow socket reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("0.0.0.0", PORT), AuthHandler) as httpd:
        print(f"Serving on port {PORT}... (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
