"""Commands: list-albums, list-photos, and mcp."""
"""Command line for the photo feed.

Examples:
    python3 -m photo_feed list-albums
    python3 -m photo_feed list-photos
    python3 -m photo_feed list-photos --download
    python3 -m photo_feed mcp
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from photo_feed.errors import PhotoFeedError
from photo_feed.google_photos import fetch_html as default_fetch_html
from photo_feed.mcp_server import serve
from photo_feed.service import albums_document, photos_document
from photo_feed.sources import repo_root


def main(
    argv: list[str] | None = None,
    *,
    root: Path | None = None,
    env: dict[str, str] | None = None,
    stdout=None,
    stderr=None,
    stdin=None,
    fetch_html=None,
    fetch_file=None,
) -> int:
    """Run one command. Returns a process exit code."""

    argv = list(sys.argv[1:] if argv is None else argv)
    env = dict(os.environ if env is None else env)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    stdin = stdin or sys.stdin
    root = root or repo_root()
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1

    try:
        if args.command == "list-albums":
            document = albums_document(root, env)
        elif args.command == "list-photos":
            download_dir = Path(args.download) if args.download else None
            document = photos_document(
                root,
                env,
                url=args.url,
                name=args.name,
                download_dir=download_dir,
                fetch_html=fetch_html or default_fetch_html,
                fetch_file=fetch_file,
            )
            if document.get("warning"):
                print(document["warning"], file=stderr)
        elif args.command == "mcp":
            serve(
                stdin,
                stdout,
                root=root,
                env=env,
                fetch_html=fetch_html or default_fetch_html,
                fetch_file=fetch_file,
            )
            return 0
        else:
            return _fail(f"Unknown command {args.command}.", stdout, stderr)
    except (PhotoFeedError, ValueError) as exc:
        return _fail(str(exc), stdout, stderr)
    _write_json(document, stdout)
    return 0
import sys
from pathlib import Path

from photo_feed import __version__
from photo_feed.errors import AlbumError
from photo_feed.mcp_server import serve
from photo_feed.paths import repo_root
from photo_feed.service import list_album_photos, list_albums


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "mcp":
        serve()
        return 0
    if args.command is None:
        parser.print_help()
        return 0

    root = repo_root()
    try:
        if args.command == "list-albums":
            payload = list_albums(root)
        elif args.command == "list-photos":
            download_dir = Path(args.download_dir) if args.download_dir else None
            if download_dir is not None and not download_dir.is_absolute():
                download_dir = root / download_dir
            payload = list_album_photos(
                root,
                album_id=args.album,
                url=args.url,
                limit=args.limit,
                download=args.download or download_dir is not None,
                download_dir=download_dir,
            )
        else:
            parser.print_help()
            return 2
    except AlbumError as exc:
        payload = {"error": str(exc)}

    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 1 if payload.get("error") else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m photo_feed",
        description="List photos and videos from a public Google Photos shared album.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-albums", help="Show the album links this tool will use")
    photos = commands.add_parser("list-photos", help="List photos and videos in one album")
    photos.add_argument("--url", help="Shared album link. If you skip this, the saved link is used.")
    photos.add_argument("--name", help="Album name from list-albums")
    photos.add_argument(
        "--download",
        metavar="FOLDER",
        help="Save copies into this folder. Keep the folder git-ignored.",
    )
    commands.add_parser("mcp", help="Speak MCP on stdin/stdout so a bot can call this tool")
    return parser


def _write_json(document: dict, stdout) -> None:
    json.dump(document, stdout, indent=2, ensure_ascii=False)
    stdout.write("\n")


def _fail(message: str, stdout, stderr) -> int:
    print(message, file=stderr)
    _write_json({"error": message}, stdout)
    return 1


if __name__ == "__main__":
    sys.exit(main())
        prog="photo-feed",
        description=(
            "Read photos and videos from a public shared album link. "
            "Links are read from the PHOTO_FEED_URL environment variable, "
            "then a config file (PHOTO_FEED_CONFIG or photo-feed.local.json), "
            "then files in shared-album-link-storage/."
        ),
    )
    parser.add_argument("--version", action="version", version=f"photo-feed {__version__}")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("list-albums", help="Show the album links this tool will read.")

    photos = commands.add_parser("list-photos", help="List photos and videos as JSON.")
    photos.add_argument(
        "url",
        nargs="?",
        help="One shared album link. If you leave this out, the configured link is used.",
    )
    photos.add_argument("--album", help="Album id printed by list-albums.")
    photos.add_argument("--limit", type=int, help="Maximum number of items to return.")
    photos.add_argument(
        "--download",
        action="store_true",
        help="Save files into the downloads folder (that folder is not committed).",
    )
    photos.add_argument(
        "--download-dir",
        help="Folder for saved files. Inside this project, use downloads or output.",
    )

    commands.add_parser("mcp", help="Speak MCP on stdin/stdout so a bot can call this tool.")
    return parser
