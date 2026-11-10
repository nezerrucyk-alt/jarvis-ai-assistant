"""Optional, explicitly enabled HTTPS bridge from the Jarvis desktop to Android."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import shutil
import socket
import ssl
import tempfile
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from cryptography import x509


MAX_REQUEST_BYTES = 18_000
MAX_PROMPT_CHARS = 4_000
MAX_HISTORY_ITEMS = 20
MAX_HISTORY_CHARS = 10_000


def _lan_ipv4_addresses() -> list[str]:
    found: set[str] = set()
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 80))
            found.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(item[4][0])
    except OSError:
        pass
    addresses = []
    for raw in sorted(found):
        try:
            ip = ipaddress.ip_address(raw)
            if ip.version == 4 and ip.is_private and not ip.is_loopback and not ip.is_link_local:
                addresses.append(str(ip))
        except ValueError:
            continue
    return addresses or ["127.0.0.1"]


class MobileBridge:
    """A temporary, token-protected HTTPS endpoint; never starts on its own."""

    def __init__(self, answer: Callable[[str, str, list[dict]], str], port: int = 8765):
        self.answer = answer
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._token = ""
        self._fingerprint = ""
        self._temp_dir: Path | None = None
        self._lock = threading.RLock()
        self._rate_lock = threading.Lock()
        self._last_request: dict[str, float] = {}
        self._slots = threading.BoundedSemaphore(3)

    @property
    def is_running(self) -> bool:
        return self._httpd is not None

    def start(self) -> dict:
        with self._lock:
            if self._httpd is not None:
                return self.credentials()
            ips = _lan_ipv4_addresses()
            temp_dir = Path(tempfile.mkdtemp(prefix="jarvis-mobile-"))
            try:
                cert_pem, key_pem, fingerprint = self._make_certificate(ips)
                cert_path = temp_dir / "server-cert.pem"
                key_path = temp_dir / "server-key.pem"
                cert_path.write_bytes(cert_pem)
                key_path.write_bytes(key_pem)
                token = secrets.token_urlsafe(32)
                owner = self

                class Handler(BaseHTTPRequestHandler):
                    server_version = "JarvisBridge"
                    sys_version = ""

                    def log_message(self, fmt, *args):
                        logging.info("Mobile bridge %s %s", self.client_address[0], fmt % args)

                    def _send(self, code: int, payload: dict):
                        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        self.send_response(code)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("X-Content-Type-Options", "nosniff")
                        self.end_headers()
                        self.wfile.write(data)

                    def do_GET(self):
                        if self.path != "/health":
                            self._send(404, {"error": "not found"})
                            return
                        self._send(200, {"service": "JARVIS", "status": "ready"})

                    def do_POST(self):
                        if self.path != "/api/chat":
                            self._send(404, {"error": "not found"})
                            return
                        supplied = self.headers.get("Authorization", "")
                        if not hmac.compare_digest(supplied, "Bearer " + owner._token):
                            self._send(401, {"error": "Невірний токен доступу."})
                            return
                        try:
                            size = int(self.headers.get("Content-Length", "0"))
                        except ValueError:
                            size = 0
                        if size <= 0 or size > MAX_REQUEST_BYTES:
                            self._send(413, {"error": "Запит завеликий."})
                            return
                        peer = self.client_address[0]
                        now = time.monotonic()
                        with owner._rate_lock:
                            if now - owner._last_request.get(peer, 0.0) < 1.0:
                                self._send(429, {"error": "Зачекай секунду перед наступним запитом."})
                                return
                            owner._last_request[peer] = now
                        if not owner._slots.acquire(blocking=False):
                            self._send(429, {"error": "Зараз Jarvis уже відповідає. Спробуй трохи пізніше."})
                            return
                        try:
                            raw = self.rfile.read(size)
                            payload = json.loads(raw.decode("utf-8"))
                            prompt = str(payload.get("text", "")).strip()
                            mode = "coder" if payload.get("mode") == "coder" else "natural"
                            if not prompt or len(prompt) > MAX_PROMPT_CHARS:
                                self._send(400, {"error": "Повідомлення має містити до 4000 символів."})
                                return
                            incoming = payload.get("history", [])
                            history: list[dict] = []
                            if isinstance(incoming, list):
                                total = 0
                                for item in incoming[-MAX_HISTORY_ITEMS:]:
                                    if not isinstance(item, dict) or item.get("role") not in ("user", "assistant"):
                                        continue
                                    content = str(item.get("content", ""))[:2_000]
                                    total += len(content)
                                    if total > MAX_HISTORY_CHARS:
                                        break
                                    history.append({"role": item["role"], "content": content})
                            reply = owner.answer(prompt, mode, history)
                            self._send(200, {"reply": str(reply)[:20_000]})
                        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
                            self._send(400, {"error": "Некоректний формат запиту."})
                        except Exception:
                            logging.exception("Mobile bridge response failed")
                            self._send(502, {"error": "Jarvis не зміг отримати відповідь від моделі."})
                        finally:
                            owner._slots.release()

                httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
                httpd.daemon_threads = True
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.load_cert_chain(str(cert_path), str(key_path))
                httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
                self._temp_dir = temp_dir
                self._token = token
                self._fingerprint = fingerprint
                self._last_request.clear()
                self._httpd = httpd
                self._thread = threading.Thread(target=httpd.serve_forever, name="JarvisMobileBridge", daemon=True)
                self._thread.start()
                return self.credentials()
            except Exception:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise

    def credentials(self) -> dict:
        if self._httpd is None:
            raise RuntimeError("Мобільне підключення вимкнене.")
        return {
            "urls": [f"https://{ip}:{self.port}" for ip in _lan_ipv4_addresses()],
            "token": self._token,
            "fingerprint": self._fingerprint,
        }

    def stop(self) -> None:
        with self._lock:
            httpd, thread = self._httpd, self._thread
            if httpd is None:
                return
            self._httpd = None
            self._thread = None
            self._token = ""
            self._fingerprint = ""
            try:
                httpd.shutdown()
                httpd.server_close()
            finally:
                if thread and thread.is_alive():
                    thread.join(timeout=2.0)
                if self._temp_dir:
                    shutil.rmtree(self._temp_dir, ignore_errors=True)
                    self._temp_dir = None
                self._last_request.clear()

    @staticmethod
    def _make_certificate(ips: list[str]) -> tuple[bytes, bytes, str]:
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "JARVIS Android companion")])
        sans = [x509.DNSName("localhost")]
        for raw in set(ips + ["127.0.0.1"]):
            sans.append(x509.IPAddress(ipaddress.ip_address(raw)))
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(minutes=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=2))
            .add_extension(x509.SubjectAlternativeName(sans), critical=False)
            .sign(key, hashes.SHA256())
        )
        cert_der = cert.public_bytes(serialization.Encoding.DER)
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
        return cert_pem, key_pem, fingerprint
