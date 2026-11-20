# Photo feed

**Put album links in a secret, not in this repo.** This GitHub repository is public. Anyone can open a file that has been committed, including `shared-album-link-storage/MCP-Photo-Feed`. A Google Photos share link is enough to view the album. Save the link as the `PHOTO_FEED_URL` Codespaces secret (steps below). When you have done that, delete the link from the file. You can leave the file where it is.

## What this does

This is a small Python tool. You give it a public Google Photos shared-album link. It prints the photos and videos in that album: a direct file link, an id or a filename, and the date or file size when the page includes them.

It does not log into Google. It reads the same page a browser opens for someone who has the link.

A bot in Cursor can call it too. The bot uses two tools: `list_albums` and `list_album_photos`.

## What you need

Python 3.10 or newer. A Codespace made from this repo already has Python. The dev container installs nothing else. There is no `pip install` step.

On a 2017 Intel Mac, outside a Codespace:

1. Press Command and the space bar together. Type `Terminal`. Press Return.
2. Type `python3 --version` and press Return.
3. If the Mac says `command not found`, download Python from [python.org/downloads/macos](https://www.python.org/downloads/macos/). Use the macOS 64-bit installer. That installer works on Intel Macs. Quit Terminal, open it again, and run `python3 --version` once more.

## How a link is chosen

The tool stops at the first place that has a link.

1. The environment variable `PHOTO_FEED_URL`. In a Codespace this is the secret.
2. A file named `photo-feed.local.json` in this folder. Git ignores that file, so it is not uploaded. You can point `PHOTO_FEED_CONFIG` at a file outside this folder if you want the link kept somewhere else on your Mac.
3. Text files under `shared-album-link-storage/`. Empty files are skipped. A link is already stored in `shared-album-link-storage/MCP-Photo-Feed`.

## Add a link on your Mac

Copy the example file and edit the copy:

```bash
cp photo-feed.local.json.example photo-feed.local.json
```

Open `photo-feed.local.json`, replace the placeholder with your link, and save. Do not commit that file.

For one Terminal window only, you can also run:

```bash
export PHOTO_FEED_URL='https://photos.app.goo.gl/paste-your-link-here'
```

That command is saved in Terminal history. The secret, or `photo-feed.local.json`, is a better place for a private link.

In the Google Photos app: open the album, tap Share, then Create link. Copy that link. Link sharing has to be turned on.

## Set the PHOTO_FEED_URL Codespaces secret

1. On GitHub, open this repository.
2. Click **Settings**. Use the repository Settings tab, not your account settings.
3. In the left sidebar, open **Secrets and variables**, then **Codespaces**.
4. Click **New repository secret**.
5. Name: `PHOTO_FEED_URL`
6. Value: the shared album link, starting with `https://`
7. Click **Add secret**.

Stop the Codespace and start it again. A secret is loaded when the Codespace starts. A Codespace that is already running does not see a secret you just created.

The secret is not written into the repo. This project has no GitHub Actions workflow, on purpose. Do not add one that fetches the album or uploads the photo list.

## Run it

Open Terminal in this project folder. In a Codespace, the window is already there. On your Mac, type `cd ` with a space after it, drag the project folder into the window, and press Return.

Show which link will be used:

```bash
python3 -m photo_feed list-albums
```

Print the photos and videos as JSON:

```bash
python3 -m photo_feed list-photos
```

Save copies into a `downloads` folder. Git ignores that folder.

```bash
python3 -m photo_feed list-photos --download downloads
```

If you pick a folder that git does not ignore, the tool prints a warning. Do not commit that folder.

To pass one link without saving it:

```bash
python3 -m photo_feed list-photos --url 'https://photos.app.goo.gl/paste-your-link-here'
```

Check the program without opening your album. This uses a fake page in the tests. It does not use your link.

```bash
python3 -m unittest discover -s tests
```

You want a final line that says `OK`.

## What the JSON looks like

A real run prints your album. This sample is fake, so the README does not contain a real photo link.

```json
{
  "album": {
    "name": "PHOTO_FEED_URL",
    "title": "Picnic",
    "provider": "google-photos"
  },
  "items": [
    {
      "id": "fixture-photo-1",
      "filename": "picnic.jpg",
      "kind": "photo",
      "url": "https://cdn.example.test/picnic.jpg",
      "width": 800,
      "height": 600,
      "created_at": "2023-11-14T22:13:20Z",
      "size_bytes": 2048
    }
  ]
}
```

`kind` is `photo` or `video`. Filename, dates, and `size_bytes` are filled in when Google's page includes them. Otherwise they are `null`.

The public page includes the first batch of items, about 300. A bigger album is cut off, because Google only sends the rest when a person scrolls. The `note` field in the JSON says this too.

This reads Google's public share page. It is not an official API. Google removed the official way for apps to read albums. If Google changes the page, the list can come back empty until this tool is updated.

## How a bot connects

This project includes `.cursor/mcp.json`. Cursor starts the tool as an MCP server with:

```bash
python3 -m photo_feed mcp
```

The bot gets two tools:

| Tool | What you ask for | What it returns |
| --- | --- | --- |
| `list_albums` | nothing | The saved links, and which place they came from |
| `list_album_photos` | optional `url`, `name`, or `download_dir` | Photos and videos. `download_dir` also saves copies on this computer |

In Cursor:

1. Open this project folder. The server starts in that folder, so it can see the secret and the link files.
2. Open Settings, then MCP. Turn on `photo-feed` if it is off.
3. Start a new chat. Ask the bot to list the album photos.

In a Codespace, rebuild or restart it after you add `PHOTO_FEED_URL`, then start the chat. The bot reads the same secret the Terminal sees.

You do not need to run `python3 -m photo_feed mcp` yourself. Cursor runs it. If you do run it, the window sits and waits. Press Control-C to stop it.

## TeraBox

TeraBox links are recognized, then refused. TeraBox asks for a signed-in cookie and often a captcha before it will list files, and each file link is signed. This tool does not log in. It also does not send your link to a third-party downloader, because that would hand a private album to someone else.

Use a Google Photos share link. The empty files under `shared-album-link-storage/terabox-link-album/` are left where they are.

## Privacy

- Do not commit photos, thumbnails, image links from an album, JSON output, or `photo-feed.local.json`.
- `.gitignore` ignores `downloads/`, `output/`, `photo-feed-downloads/`, `photo-feed-out/`, and `photo-feed.local.json`.
- Do not add a GitHub Actions workflow that opens the album or publishes the list.
- The photo list is printed in your Terminal, or returned to the bot. It is not stored in git unless you commit it yourself.
**Your albums are private. This GitHub repo is public.** A link that is saved in a file here can be seen by anyone on the internet, including in old commits. Put the real link in the `PHOTO_FEED_URL` Codespaces secret (steps below) and do not paste album pages, photo lists, or downloaded pictures into the repo or into a public chat.

The file `shared-album-link-storage/MCP-Photo-Feed` is already committed. Deleting it later does not erase it from older commits. If that album should stay private, turn off link sharing in Google Photos and create a new link. Save the new link only as the secret.

This folder is a small tool that reads a **public shared album link** and prints a list of the photos and videos. A bot (in Cursor, or another app that speaks MCP) can ask for that list. You do not install extra Python packages. The tool does not log in to Google or TeraBox.

It reads the same page a browser shows for "anyone with the link." It does not use the Google Photos API.

## What you need

- A shared album link from Google Photos: open the album, tap **Share**, then **Create link**. The link looks like `https://photos.app.goo.gl/...`. It has to be the "anyone with the link" kind. A private share that only certain Google accounts can open will not work, because this tool does not sign in.
- Python 3.10 or newer. In a GitHub Codespace, Python is already installed. On your Mac, check with the command in the next section.

A Codespace is a small computer GitHub runs in the cloud. Your 2017 Intel Mac only has to open a browser. The old Mac does not have to do the work.

## Check Python on the Mac

1. Open **Terminal** (search for Terminal in Spotlight).
2. Paste this and press Return:

```bash
python3 --version
```

3. If you see `Python 3.10` or a higher number, you are set.
4. If the command is not found, install Python from [python.org/downloads](https://www.python.org/downloads/). Use the macOS installer. It works on Intel Macs. Then close Terminal, open it again, and run the version command once more.

## Where the tool looks for a link

It stops at the first place that has a link:

1. The environment variable `PHOTO_FEED_URL` (this is the Codespaces secret).
2. A local config file. By default that is `photo-feed.local.json` in this folder. Git ignores that file, so it is not uploaded. To keep the file somewhere else, set `PHOTO_FEED_CONFIG` to its path (for example `~/albums/photo-feed.local.json`).
3. Text files under `shared-album-link-storage/`. Empty files are skipped. A line that starts with `#` is a note, not a link.

## Set the PHOTO_FEED_URL secret

Do this in a browser, on GitHub. You must be the owner of the repo.

1. Open the `cloud-albums-links` repository on GitHub.
2. Click **Settings**.
3. In the left sidebar, open **Secrets and variables**, then **Codespaces**.
4. Click **New repository secret**.
5. Name: `PHOTO_FEED_URL` (all capitals, exactly that).
6. Value: paste the shared album link and nothing else.
7. Click **Add secret**.

Stop any codespace that is already running and create a new one so it can see the secret. GitHub does not update the secret inside a codespace that is already open.

The secret is **not** put in the repo, and it is **not** given to GitHub Actions. This project does not have a GitHub Actions workflow on purpose.

### Use the secret in a Codespace

1. On the repo page, click **Code**, then **Codespaces**, then **Create codespace** on this branch (after it is merged, `main` is fine).
2. Wait until the terminal is ready. The setup runs the tests, which use a fake album page. They do not open your album.
3. In the codespace terminal:

```bash
python3 -m photo_feed list-albums
python3 -m photo_feed list-photos
```

`list-albums` prints which link will be used. `list-photos` prints the photos and videos as JSON (a text format programs can read).

### Use a link on the Mac instead

The Codespaces secret exists only inside a Codespace. Cursor on the Mac does not see it.

From the project folder:

```bash
cd cloud-albums-links
cp photo-feed.local.json.example photo-feed.local.json
```

Open `photo-feed.local.json` in a text editor and replace the example link with your real link. Save. That file is git-ignored. If you would rather keep that file outside the project, put it somewhere else and point at it:

```bash
export PHOTO_FEED_CONFIG="$HOME/albums/photo-feed.local.json"
```

`PHOTO_FEED_URL` still wins when it is set. A one-link secret is the right choice in a Codespace. `PHOTO_FEED_CONFIG` is for a file on your Mac.

You can also type this in Terminal. It lasts until you close the window, and the link is saved in Terminal's command history, so the file is the better choice:

```bash
export PHOTO_FEED_URL='paste-the-link-here'
python3 -m photo_feed list-photos
```

## Run it

From the project folder:

```bash
python3 -m photo_feed --help
python3 -m photo_feed list-albums
python3 -m photo_feed list-photos
```

Read one link without saving it in config:

```bash
python3 -m photo_feed list-photos 'https://photos.app.goo.gl/paste-your-link-here'
```

Save copies of the files on this computer only (not on GitHub):

```bash
python3 -m photo_feed list-photos --download
```

Files go in `downloads/`. That folder is git-ignored, so the command stays quiet. If you pick another folder and git is not ignoring it, the command prints a warning: this repo is public, so do not commit the photos. You can also use `output/` if you want to save the JSON:

```bash
python3 -m photo_feed list-photos > output/list.json
```

Do not commit `downloads/` or `output/`. Do not paste that JSON into a public place. It contains direct links to the photos.

A made-up example of what one item looks like (this is not a real photo):

```json
{
  "id": "fixture-photo-1",
  "filename": "fixture-photo-1.jpg",
  "kind": "image",
  "url": "https://lh3.googleusercontent.com/pw/EXAMPLE_NOT_A_REAL_PHOTO=s2048",
  "original_url": "https://lh3.googleusercontent.com/pw/EXAMPLE_NOT_A_REAL_PHOTO=d",
  "width": 800,
  "height": 600,
  "date": "2024-03-09T16:00:00Z",
  "size_bytes": null
}
```

- `url` is a direct link, sized for viewing.
- `original_url` asks Google for the original file. `--download` saves that one. For a video, this is the file itself when Google allows it.
- `date` is the date on the public page, when Google includes one.
- `size_bytes` is the file size when the page includes one. Google's public page usually does not, so this is often `null`.
- `kind` is `image` or `video`. A video is marked when the page says it is a video.

## How a bot connects

This repo includes `.cursor/mcp.json`. That file tells Cursor to start a small helper called an MCP server. The helper's name is `photo-feed`. It has two tools:

- `list_albums` — which albums are configured
- `list_album_photos` — the photos and videos in one album

In Cursor:

1. Open this project folder (on the Mac, or the Codespace).
2. Open **Cursor Settings → MCP**.
3. Turn on **photo-feed**. If it is missing, reload the window (Command-Shift-P, then "Reload Window").
4. In chat, ask the bot to list the photos in the album. It should call those tools. You do not paste the album page into the chat.

The bot only sees a link that is available **where the bot is running**:

- Bot inside the Codespace: the `PHOTO_FEED_URL` secret is enough.
- Bot in Cursor on the Mac: use `photo-feed.local.json` on the Mac, or start Cursor from a Terminal where `PHOTO_FEED_URL` is set. The Codespaces secret is not on the Mac.

Other apps that speak MCP can use the same command:

```json
{
  "mcpServers": {
    "photo-feed": {
      "command": "python3",
      "args": ["-m", "photo_feed", "mcp"],
      "env": {
        "PYTHONPATH": "/full/path/to/cloud-albums-links"
      }
    }
  }
}
```

Replace the path with the real folder on your Mac.

## TeraBox

TeraBox share links are recognized and then refused, with a short explanation. A TeraBox share page does not include the file list in the HTML. Reading it means running TeraBox's anti-bot script and then asking for a signed download link, which often comes back as a captcha from a Codespace. This tool will not sign in and will not send your link to another website's downloader. Use a Google Photos link for the bot.

## Limits

- Only albums shared so **anyone with the link** can view them.
- A short `photos.app.goo.gl` link is fine. Google redirects a simple request to the album page. This tool follows that redirect.
- A large album comes back as the first batch on that page (often about 300 items). The JSON then has `"partial": true`. Google loads the rest only when a person scrolls, and this tool does not pretend to scroll. If the page only contains links to each photo, the tool opens up to 40 of those pages. Use `--limit` to take fewer.
- Google sometimes changes the page. If the link works in a browser but this tool says no photos were found, the page format changed and the parser needs an update.
- The tool does not upload anything and it does not start a website.

## Tests

The tests use a fake album page stored in `tests/fixtures/`. They do not open your album and they do not print what is in it.

```bash
python3 -m unittest discover -s tests
```

## Project files

| Path | What it is |
| --- | --- |
| `photo_feed/` | The program |
| `shared-album-link-storage/` | Optional link files. Prefer the secret. |
| `photo-feed.local.json.example` | A sample config. Copy it to `photo-feed.local.json`. |
| `.cursor/mcp.json` | How Cursor starts the bot helper |
| `.devcontainer/` | How the Codespace is built |
| `downloads/` and `output/` | Created when you ask. Git ignores them. |
