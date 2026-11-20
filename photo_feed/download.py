"""Save photos and videos into a folder on this computer.

Nothing here uploads a file. Callers pass the folder, and that folder should
stay in .gitignore.
"""
"""Save album files locally without putting them in git."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from urllib.parse import unquote

from photo_feed.errors import PhotoFeedError
from photo_feed.google_photos import MediaItem

_MAX_BYTES = 512 * 1024 * 1024
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def fetch_bytes(url: str, *, open_url=None, timeout: int = 60) -> tuple[bytes, dict[str, str]]:
    """Download one web URL. Returns the body and response headers."""

    if not url.startswith(("http://", "https://")):
        raise PhotoFeedError("Refusing to download a non-web link.")
    if open_url is None:
        open_url = urllib.request.urlopen
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with open_url(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            if status != 200:
                raise PhotoFeedError(f"Download failed with HTTP {status}.")
            raw = response.read()
            headers = {key: value for key, value in response.headers.items()}
    except PhotoFeedError:
        raise
    except Exception as exc:
        raise PhotoFeedError("Could not download that file.") from exc
    if len(raw) > _MAX_BYTES:
        raise PhotoFeedError("That file is larger than 512 MB, so it was not saved.")
    return raw, headers


def download_items(items: list[MediaItem], dest: Path, *, fetch_bytes=fetch_bytes) -> list[dict]:
    """Write each item into ``dest``. Filenames cannot escape that folder."""

    for item in items:
        if not item.url.startswith(("http://", "https://")):
            raise PhotoFeedError(f"Refusing to download a non-web link for {item.id}.")

    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    used = {path.name for path in dest_resolved.iterdir()}
    saved: list[dict] = []
    for item in items:
        body, headers = fetch_bytes(item.url)
        preferred = _filename_from_headers(headers) or item.filename or f"{item.id}.bin"
        name = _unique_name(_safe_name(preferred, f"{item.id}.bin"), used)
        target = dest / name
        if dest_resolved not in target.resolve().parents:
            raise PhotoFeedError("Refusing to write outside the download folder.")
        target.write_bytes(body)
        saved.append({"id": item.id, "path": str(target), "bytes": len(body)})
    return saved


def _filename_from_headers(headers: dict[str, str]) -> str | None:
    disposition = ""
    for key, value in headers.items():
        if key.lower() == "content-disposition":
            disposition = value
            break
    if not disposition:
        return None
    encoded = re.search(r"filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)", disposition)
    if encoded:
        return unquote(encoded.group(1).strip())
    quoted = re.search(r'filename\s*=\s*"([^"]+)"', disposition)
    if quoted:
        return quoted.group(1)
    plain = re.search(r"filename\s*=\s*([^;]+)", disposition)
    if plain:
        return plain.group(1).strip().strip('"')
    return None


def _safe_name(name: str, fallback: str) -> str:
    cleaned = unquote(name).replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", cleaned).strip("._ ")
    if not cleaned or cleaned in {".", ".."}:
        return fallback
    return cleaned[:180]


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix
    number = 2
    while True:
        candidate = f"{stem}-{number}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        number += 1
import subprocess
from pathlib import Path

from photo_feed.errors import AlbumError

_ALLOWED_TOP_FOLDERS = {"downloads", "output"}


def ensure_safe_download_dir(root: Path, dest: Path) -> Path:
    """Allow downloads outside the project, or only in downloads/ and output/ inside it."""
    root = root.resolve()
    dest = dest.resolve()
    if ".git" in dest.parts:
        raise AlbumError("Refusing to save photos into a .git folder.")
    try:
        relative = dest.relative_to(root)
    except ValueError:
        return dest
    if not relative.parts or relative.parts[0] not in _ALLOWED_TOP_FOLDERS:
        raise AlbumError(
            "Inside this project, photos can only be saved to the downloads or output folders. "
            "Those folders are git-ignored so the photos stay off GitHub."
        )
    return dest


def download_commit_warning(path: Path) -> str | None:
    """Warn when a saved photo would be committable in a public repo.

    ``path`` is a file path inside the download folder (it does not have to exist).
    Git is asked with ``check-ignore``. Outside a git repo, or if git cannot
    answer, there is no warning and no error.
    """
    path = Path(path)
    if _git_ignores(path) is not False:
        return None
    folder = path.parent if path.suffix else path
    return (
        f"Warning: photos were saved to {folder}. "
        "Git is not ignoring that folder. This repo is public. "
        "Do not commit these photos."
    )


def _git_ignores(path: Path) -> bool | None:
    """True if git ignores path, False if it does not, None if git cannot say."""
    start = path if path.is_dir() else path.parent
    while not start.exists():
        if start.parent == start:
            return None
        start = start.parent
    toplevel = _git(["rev-parse", "--show-toplevel"], start)
    if toplevel is None:
        return None
    repo = toplevel.stdout.strip()
    if not repo:
        return None
    checked = _git(["check-ignore", "-q", "--", str(path)], Path(repo))
    if checked is None:
        return None
    if checked.returncode == 0:
        return True
    if checked.returncode == 1:
        return False
    return None


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def file_path_for(dest: Path, filename: str, used: set[str]) -> Path:
    """Build a file path that stays inside dest, even if the name tries to climb out."""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._") or "photo"
    candidate_name = safe
    number = 2
    while candidate_name.lower() in used:
        stem = Path(safe).stem
        suffix = Path(safe).suffix
        candidate_name = f"{stem}-{number}{suffix}"
        number += 1
    used.add(candidate_name.lower())
    candidate = (dest / candidate_name).resolve()
    candidate.relative_to(dest)
    return candidate
