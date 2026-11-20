"""MCP server over stdin and stdout.

The protocol is newline-delimited JSON-RPC. Album contents go in the tool
result only. This process does not print them anywhere else.
"""A small MCP server so a bot can call list_albums and list_album_photos.

The server speaks JSON-RPC over stdin and stdout, with Content-Length headers.
Nothing is written to stdout except protocol messages. Album contents stay in
those messages, which go to the bot, not to a log file.
"""

from __future__ import annotations

import json
from pathlib import Path

from photo_feed import __version__
from photo_feed.errors import PhotoFeedError
from photo_feed.service import albums_document, photos_document

_PROTOCOL = "2024-11-05"
_SUPPORTED = {"2024-11-05", "2025-03-26", "2025-06-18"}
import sys
from pathlib import Path

from photo_feed import __version__
from photo_feed.errors import AlbumError
from photo_feed.paths import repo_root
from photo_feed.service import list_album_photos, list_albums

_SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}

_TOOLS = [
    {
        "name": "list_albums",
        "description": (
            "List the shared album links this tool knows about. "
            "Does not open the albums or download photos."
            "List the shared albums this tool can read. "
            "Links come from PHOTO_FEED_URL, then photo-feed.local.json, "
            "then shared-album-link-storage/."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "list_album_photos",
        "description": (
            "List photos and videos in one public Google Photos shared album. "
            "Pass url, or a name from list_albums. With no arguments, uses the one saved link. "
            "Optional download_dir saves copies on this computer."
            "List photos and videos in one public shared album. "
            "Each item includes a direct image URL, a filename, and any date or size the page provided."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Shared album link, such as https://photos.app.goo.gl/...",
                },
                "name": {
                    "type": "string",
                    "description": "Album name returned by list_albums.",
                },
                "download_dir": {
                    "type": "string",
                    "description": "Folder to save copies into. Leave this out to only list links.",
                "album_id": {
                    "type": "string",
                    "description": "Album id from list_albums. Optional when only one album is configured.",
                },
                "url": {
                    "type": "string",
                    "description": "A shared album link to read instead of a configured album.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of items to return.",
                },
                "download_dir": {
                    "type": "string",
                    "description": (
                        "If set, also save files there. Inside this project the folder must be "
                        "downloads or output, both of which are git-ignored."
                    ),
                },
            },
            "additionalProperties": False,
        },
    },
]


def handle(message: dict, *, root: Path, env: dict[str, str], fetch_html, fetch_file) -> dict | None:
    """Answer one JSON-RPC message. Notifications return None."""

    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid request")
    method = message.get("method")
    has_id = "id" in message
    msg_id = message.get("id")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    if isinstance(method, str) and method.startswith("notifications/"):
        return None
    if method == "initialize":
        version = params.get("protocolVersion") or _PROTOCOL
        if version not in _SUPPORTED:
            version = _PROTOCOL
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "photo-feed", "version": __version__},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": _TOOLS}}
    if method == "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": _call_tool(
                params.get("name"),
                params.get("arguments") or {},
                root=root,
                env=env,
                fetch_html=fetch_html,
                fetch_file=fetch_file,
            ),
        }
    if not has_id:
        return None
    return _error(msg_id, -32601, "Unknown method")


def serve(stdin, stdout, *, root: Path, env: dict[str, str], fetch_html, fetch_file) -> None:
    """Read JSON-RPC messages until stdin closes."""

    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "Parse error")
        else:
            response = handle(
                message,
                root=root,
                env=env,
                fetch_html=fetch_html,
                fetch_file=fetch_file,
            )
        if response is None:
            continue
        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()


def _call_tool(name, arguments, *, root, env, fetch_html, fetch_file) -> dict:
def serve(stdin=None, stdout=None) -> None:
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout.buffer if stdout is None else stdout
    while True:
        try:
            message = read_message(stdin)
        except json.JSONDecodeError:
            write_message(stdout, _rpc_error(None, -32700, "Parse error"))
            continue
        if message is None:
            return
        if not isinstance(message, dict):
            write_message(stdout, _rpc_error(None, -32600, "Invalid request"))
            continue
        response = handle_message(message)
        if response is not None:
            write_message(stdout, response)


def handle_message(message: dict, root: Path | None = None, fetch_text=None, fetch_download=None) -> dict | None:
    method = message.get("method")
    if not isinstance(method, str):
        return _rpc_error(message.get("id"), -32600, "Invalid request")
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        return _initialize(message)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"tools": _TOOLS}}
    if method == "tools/call":
        return _call_tool(message, root or repo_root(), fetch_text, fetch_download)
    return _rpc_error(message.get("id"), -32601, "Method not found")


def read_message(stream):
    """Read one MCP message. Accepts Content-Length frames or one JSON line."""
    line = stream.readline()
    if line == b"":
        return None
    if line.lstrip().startswith(b"{"):
        return json.loads(line.decode("utf-8"))

    headers = {}
    current = line
    while current not in (b"\r\n", b"\n"):
        if current == b"":
            return None
        text = current.decode("ascii", errors="replace").strip()
        if ":" in text:
            key, value = text.split(":", 1)
            headers[key.lower()] = value.strip()
        current = stream.readline()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        raise json.JSONDecodeError("missing body", "", 0)
    body = stream.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(stream, message: dict) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stream.write(body)
    flush = getattr(stream, "flush", None)
    if flush:
        flush()


def _initialize(message: dict) -> dict:
    params = message.get("params") or {}
    client_version = params.get("protocolVersion") if isinstance(params, dict) else None
    version = client_version if client_version in _SUPPORTED_PROTOCOLS else "2024-11-05"
    return {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "photo-feed", "version": __version__},
            "instructions": (
                "Lists public shared albums configured with PHOTO_FEED_URL, "
                "photo-feed.local.json, or shared-album-link-storage. "
                "Does not log in and does not upload photos."
            ),
        },
    }


def _call_tool(message: dict, root: Path, fetch_text, fetch_download) -> dict:
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _rpc_error(message.get("id"), -32602, "Invalid tool call")
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        arguments = {}
    try:
        if name == "list_albums":
            payload = albums_document(root, env)
        elif name == "list_album_photos":
            download_dir = arguments.get("download_dir")
            payload = photos_document(
                root,
                env,
                url=arguments.get("url") if isinstance(arguments.get("url"), str) else None,
                name=arguments.get("name") if isinstance(arguments.get("name"), str) else None,
                download_dir=Path(download_dir) if isinstance(download_dir, str) and download_dir.strip() else None,
                fetch_html=fetch_html,
                fetch_file=fetch_file,
            )
        else:
            return _tool_error(f"Unknown tool {name}.")
    except (PhotoFeedError, ValueError) as exc:
        return _tool_error(str(exc))
    except Exception:
        return _tool_error("Something went wrong while reading the album.")
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}],
        "isError": False,
    }


def _tool_error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _error(msg_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
            payload = list_albums(root)
        elif name == "list_album_photos":
            download_dir = arguments.get("download_dir") or None
            dest = None
            if isinstance(download_dir, str) and download_dir.strip():
                dest = Path(download_dir)
                if not dest.is_absolute():
                    dest = root / dest
            limit = arguments.get("limit")
            payload = list_album_photos(
                root,
                album_id=arguments.get("album_id") or None,
                url=arguments.get("url") or None,
                limit=limit if isinstance(limit, int) else None,
                download=dest is not None,
                download_dir=dest,
                fetch_text=fetch_text,
                fetch_download=fetch_download,
            )
        else:
            return _rpc_error(message.get("id"), -32602, f"Unknown tool: {name}")
    except AlbumError as exc:
        payload = {"error": str(exc)}

    return {
        "jsonrpc": "2.0",
        "id": message.get("id"),
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2, ensure_ascii=False),
                }
            ],
            "isError": bool(payload.get("error")),
        },
    }


def _rpc_error(message_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}
