#!/usr/bin/env python3
"""Serve JeopardyPartyNight and relay room messages on a local network."""

from __future__ import annotations

import argparse
import ipaddress
import json
import secrets
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8000
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
MAX_BODY = 64 * 1024
POLL_TIMEOUT = 15
ROOMS: dict[str, "Room"] = {}
ROOMS_LOCK = threading.Lock()


class Room:
    def __init__(self, host_id: str) -> None:
        self.host_id = host_id
        self.clients: dict[str, deque[dict[str, object]]] = {}
        self.host_messages: deque[dict[str, object]] = deque()
        self.redirect_code: str | None = None
        self.condition = threading.Condition()


def json_bytes(data: object) -> bytes:
    return json.dumps(data, separators=(",", ":")).encode("utf-8")


def lan_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = result[4][0]
            ip = ipaddress.ip_address(address)
            if not ip.is_loopback and not ip.is_link_local:
                addresses.add(address)
    except OSError:
        pass
    if not addresses:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 80))
            address = probe.getsockname()[0]
            ip = ipaddress.ip_address(address)
            if not ip.is_loopback and not ip.is_link_local:
                addresses.add(address)
        except OSError:
            pass
        finally:
            probe.close()
    return sorted(addresses, key=lambda value: not ipaddress.ip_address(value).is_private)


class Handler(BaseHTTPRequestHandler):
    server_version = "JeopardyLAN/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, status: int, data: object) -> None:
        body = json_bytes(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            raise ValueError("Request body must be between 1 byte and 64 KB.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        return data

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json(200, {"ok": True})
            return
        if parsed.path == "/api/room/poll":
            self.poll_room(parse_qs(parsed.query))
            return
        if parsed.path not in ("/", "/index.html", "/README.md"):
            self.send_error(404)
            return
        path = ROOT / ("index.html" if parsed.path == "/" else parsed.path.lstrip("/"))
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        content_type = "text/html; charset=utf-8" if path.suffix == ".html" else "text/markdown; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            data = self.read_json()
            if self.path == "/api/room/create":
                self.create_room(data)
            elif self.path == "/api/room/join":
                self.join_room(data)
            elif self.path == "/api/room/send":
                self.send_room_message(data)
            else:
                self.send_error(404)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            return

    def create_room(self, data: dict[str, object]) -> None:
        previous = str(data.get("previousCode", "")).upper()
        client_id = secrets.token_urlsafe(18)
        with ROOMS_LOCK:
            while True:
                code = "".join(secrets.choice(ALPHABET) for _ in range(6))
                if code != previous and code not in ROOMS:
                    ROOMS[code] = Room(client_id)
                    break
        addresses = lan_addresses()
        port = self.server.server_port
        bases = [f"http://{address}:{port}/" for address in addresses]
        self.send_json(200, {
            "code": code,
            "clientId": client_id,
            "joinBase": bases[0] if bases else f"http://{self.headers.get('Host', f'localhost:{port}')}/",
            "joinBases": bases,
        })

    def join_room(self, data: dict[str, object]) -> None:
        code = str(data.get("code", "")).upper()
        client_id = str(data.get("clientId", ""))
        if len(client_id) > 128 or not client_id:
            self.send_json(400, {"error": "Invalid client id."})
            return
        with ROOMS_LOCK:
            room = ROOMS.get(code)
        if room is None:
            self.send_json(404, {"error": "Room not found. Check the code and make sure the host is running the LAN server."})
            return
        with room.condition:
            if room.redirect_code:
                self.send_json(200, {"redirectCode": room.redirect_code})
                return
            room.clients.setdefault(client_id, deque())
            room.condition.notify_all()
        self.send_json(200, {"ok": True})

    def poll_room(self, query: dict[str, list[str]]) -> None:
        code = query.get("code", [""])[0].upper()
        client_id = query.get("clientId", [""])[0]
        with ROOMS_LOCK:
            room = ROOMS.get(code)
        if room is None:
            self.send_json(404, {"error": "Room not found."})
            return
        deadline = time.monotonic() + POLL_TIMEOUT
        with room.condition:
            if client_id != room.host_id and client_id not in room.clients:
                self.send_json(403, {"error": "Client has not joined this room."})
                return
            queue = room.host_messages if client_id == room.host_id else room.clients[client_id]
            while not queue and not room.redirect_code:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                room.condition.wait(remaining)
            messages = list(queue)
            queue.clear()
            redirect_code = room.redirect_code if client_id != room.host_id else None
        self.send_json(200, {"messages": messages, "redirectCode": redirect_code})

    def send_room_message(self, data: dict[str, object]) -> None:
        code = str(data.get("code", "")).upper()
        client_id = str(data.get("clientId", ""))
        message_type = data.get("t")
        if not isinstance(message_type, str) or len(message_type) > 64:
            self.send_json(400, {"error": "Invalid message type."})
            return
        message = {"t": message_type, "d": data.get("d")}
        if len(json_bytes(message)) > 16 * 1024:
            self.send_json(413, {"error": "Room message is too large."})
            return
        with ROOMS_LOCK:
            room = ROOMS.get(code)
        if room is None:
            self.send_json(404, {"error": "Room not found."})
            return
        with room.condition:
            if client_id == room.host_id:
                if message_type == "new-room":
                    target = message["d"]
                    if not isinstance(target, dict) or not isinstance(target.get("code"), str):
                        self.send_json(400, {"error": "Invalid redirect room."})
                        return
                    room.redirect_code = target["code"]
                for queue in room.clients.values():
                    queue.append(message)
            elif client_id in room.clients:
                room.host_messages.append(message)
            else:
                self.send_json(403, {"error": "Client has not joined this room."})
                return
            room.condition.notify_all()
        self.send_json(200, {"ok": True})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Host JeopardyPartyNight on a local network.")
    parser.add_argument("--host", default="0.0.0.0", help="Interface to bind (default: all interfaces)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"TCP port (default: {DEFAULT_PORT}; use 0 for an available port)")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    server = Server((args.host, args.port), Handler)
    port = server.server_port
    print("Jeopardy LAN server is running.")
    print(f"On this laptop: http://localhost:{port}/")
    addresses = lan_addresses() if args.host in ("0.0.0.0", "") else []
    if addresses:
        for address in addresses:
            print(f"On the same Wi-Fi/LAN: http://{address}:{port}/")
    elif args.host not in ("0.0.0.0", ""):
        print(f"Bound to: http://{args.host}:{port}/")
    else:
        print(f"No LAN address detected. Find this laptop's IPv4 address and use port {port}.")
    print("Keep this window open. Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Jeopardy LAN server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
