#!/usr/bin/env python3
"""
SnippetVault — Developer Code Snippet Manager
Micro-SaaS MVP: Local-first snippet storage with REST API and web UI.

Usage:
    python3 server.py              # Start on port 3040 (default)
    python3 server.py --port 8080  # Custom port
    python3 server.py --host 0.0.0.0  # Listen on all interfaces

Endpoints:
    GET  /api/snippets              — list all snippets
    GET  /api/snippets/<id>         — get one snippet
    POST /api/snippets              — create snippet
    PUT  /api/snippets/<id>         — update snippet
    DELETE /api/snippets/<id>       — delete snippet
    GET  /api/snippets/search?q=    — search snippets
    GET  /api/tags                  — list all tags
    GET  /api/stats                 — snippet counts by language
    GET  /api/export                — export all snippets as JSON
    POST /api/import                — import snippets from JSON
"""

import json
import os
import re
import sys
import time
import uuid
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

DATA_FILE = Path(__file__).parent / "snippets.json"
HTML_FILE = Path(__file__).parent / "index.html"


# ─── Storage ──────────────────────────────────────────────────────────────────

def load_snippets() -> list[dict]:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_snippets(snippets: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(snippets, indent=2, ensure_ascii=False))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def snippet_valid(data: dict) -> tuple[bool, str]:
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        return False, "title is required"
    if not isinstance(data.get("code"), str) or not data["code"].strip():
        return False, "code is required"
    return True, ""


def all_tags(snippets: list[dict]) -> list[str]:
    tags = set()
    for s in snippets:
        for t in s.get("tags", []):
            tags.add(t.strip().lower())
    return sorted(tags)


def search_snippets(snippets: list[dict], query: str) -> list[dict]:
    q = query.lower()
    results = []
    for s in snippets:
        in_title = q in s.get("title", "").lower()
        in_code = q in s.get("code", "").lower()
        in_tags = any(q in t.lower() for t in s.get("tags", []))
        in_lang = q in s.get("language", "").lower()
        if in_title or in_code or in_tags or in_lang:
            # Boost results where query matches title
            score = 2 if in_title else 0
            score += 1 if in_tags else 0
            results.append((score, s))
    results.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in results]


def filter_by_tag(snippets: list[dict], tag: str) -> list[dict]:
    tag_lower = tag.strip().lower()
    return [s for s in snippets if tag_lower in (t.lower() for t in s.get("tags", []))]


def filter_by_language(snippets: list[dict], lang: str) -> list[dict]:
    lang_lower = lang.strip().lower()
    return [s for s in snippets if s.get("language", "").lower() == lang_lower]


# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class SnippetVaultHandler(BaseHTTPRequestHandler):
    """Handles API requests and serves static files."""

    # Silence default logging for cron
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _find_snippet(self, snippets: list[dict], sid: str) -> tuple[int, dict | None]:
        for i, s in enumerate(snippets):
            if s.get("id") == sid:
                return i, s
        return -1, None

    # ── CORS preflight ──

    def do_OPTIONS(self):
        self._send_json({})

    # ── GET ──

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        # Serve frontend
        if path == "" or path == "/":
            if HTML_FILE.exists():
                self._send_html(HTML_FILE.read_text())
            else:
                self._send_json({"error": "index.html not found"}, 500)
            return

        # API: health
        if path == "/api/health":
            self._send_json({"status": "ok", "snippets": len(load_snippets())})
            return

        # API: stats
        if path == "/api/stats":
            snippets = load_snippets()
            langs = {}
            tag_counts = {}
            for s in snippets:
                lang = s.get("language", "plaintext")
                langs[lang] = langs.get(lang, 0) + 1
                for t in s.get("tags", []):
                    tag_counts[t.lower()] = tag_counts.get(t.lower(), 0) + 1
            self._send_json({
                "total": len(snippets),
                "languages": langs,
                "tags": tag_counts,
            })
            return

        # API: tags
        if path == "/api/tags":
            snippets = load_snippets()
            self._send_json(all_tags(snippets))
            return

        # API: export
        if path == "/api/export":
            snippets = load_snippets()
            self._send_json({
                "exported_at": now_iso(),
                "version": "1.0",
                "snippets": snippets,
            })
            return

        # API: search
        if path == "/api/snippets/search":
            q = params.get("q", [""])[0]
            tag = params.get("tag", [None])[0]
            lang = params.get("lang", [None])[0]

            snippets = load_snippets()

            if tag:
                snippets = filter_by_tag(snippets, tag)
            if lang:
                snippets = filter_by_language(snippets, lang)
            if q:
                snippets = search_snippets(snippets, q)

            self._send_json(snippets)
            return

        # API: /api/snippets
        if path == "/api/snippets":
            snippets = load_snippets()
            tag = params.get("tag", [None])[0]
            lang = params.get("lang", [None])[0]
            if tag:
                snippets = filter_by_tag(snippets, tag)
            if lang:
                snippets = filter_by_language(snippets, lang)
            # Sort by updated desc
            snippets.sort(key=lambda s: s.get("updated", ""), reverse=True)
            self._send_json(snippets)
            return

        # API: /api/snippets/<id>
        m = re.match(r"^/api/snippets/([a-f0-9]{12})$", path)
        if m:
            sid = m.group(1)
            snippets = load_snippets()
            _, found = self._find_snippet(snippets, sid)
            if found:
                self._send_json(found)
            else:
                self._send_json({"error": "not found"}, 404)
            return

        # 404
        self._send_json({"error": "not found"}, 404)

    # ── POST ──

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Import
        if path == "/api/import":
            data = self._read_body()
            incoming = data.get("snippets", [])
            if not isinstance(incoming, list):
                self._send_json({"error": "snippets must be an array"}, 400)
                return

            snippets = load_snippets()
            imported = 0
            existing_ids = {s["id"] for s in snippets}
            for item in incoming:
                if not isinstance(item, dict):
                    continue
                sid = item.get("id", new_id())
                # Skip duplicates by id
                if sid in existing_ids:
                    continue
                item["id"] = sid
                item.setdefault("title", "Untitled")
                item.setdefault("code", "")
                item.setdefault("language", "plaintext")
                item.setdefault("tags", [])
                ts = now_iso()
                item.setdefault("created", ts)
                item["updated"] = ts
                snippets.append(item)
                existing_ids.add(sid)
                imported += 1

            save_snippets(snippets)
            self._send_json({"imported": imported, "total": len(snippets)})
            return

        # Create snippet
        if path == "/api/snippets":
            data = self._read_body()
            valid, err = snippet_valid(data)
            if not valid:
                self._send_json({"error": err}, 400)
                return

            snippets = load_snippets()
            ts = now_iso()
            snippet = {
                "id": new_id(),
                "title": data["title"].strip(),
                "code": data["code"].strip(),
                "language": data.get("language", "plaintext").strip().lower(),
                "tags": [t.strip().lower() for t in data.get("tags", []) if t.strip()],
                "description": data.get("description", "").strip(),
                "created": ts,
                "updated": ts,
            }
            snippets.append(snippet)
            save_snippets(snippets)
            self._send_json(snippet, 201)
            return

        self._send_json({"error": "not found"}, 404)

    # ── PUT ──

    def do_PUT(self):
        m = re.match(r"^/api/snippets/([a-f0-9]{12})$", urlparse(self.path).path.rstrip("/"))
        if not m:
            self._send_json({"error": "not found"}, 404)
            return

        sid = m.group(1)
        data = self._read_body()
        snippets = load_snippets()
        idx, found = self._find_snippet(snippets, sid)

        if not found:
            self._send_json({"error": "not found"}, 404)
            return

        if "title" in data:
            if not data["title"].strip():
                self._send_json({"error": "title is required"}, 400)
                return
            found["title"] = data["title"].strip()
        if "code" in data:
            if not data["code"].strip():
                self._send_json({"error": "code is required"}, 400)
                return
            found["code"] = data["code"].strip()
        if "language" in data:
            found["language"] = data["language"].strip().lower()
        if "tags" in data:
            found["tags"] = [t.strip().lower() for t in data["tags"] if t.strip()]
        if "description" in data:
            found["description"] = data["description"].strip()
        found["updated"] = now_iso()

        snippets[idx] = found
        save_snippets(snippets)
        self._send_json(found)

    # ── DELETE ──

    def do_DELETE(self):
        m = re.match(r"^/api/snippets/([a-f0-9]{12})$", urlparse(self.path).path.rstrip("/"))
        if not m:
            self._send_json({"error": "not found"}, 404)
            return

        sid = m.group(1)
        snippets = load_snippets()
        idx, found = self._find_snippet(snippets, sid)

        if not found:
            self._send_json({"error": "not found"}, 404)
            return

        deleted = snippets.pop(idx)
        save_snippets(snippets)
        self._send_json({"deleted": deleted["id"], "title": deleted["title"]})


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SnippetVault — Developer Code Snippet Manager")
    parser.add_argument("--port", type=int, default=3040, help="Port to listen on (default: 3040)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    args = parser.parse_args()

    # Ensure data file exists
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]")

    server = HTTPServer((args.host, args.port), SnippetVaultHandler)
    print(f"SnippetVault running on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()