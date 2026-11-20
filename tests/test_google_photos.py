"""Parse a saved Google Photos share page that contains no real album."""

import gzip
import unittest
from pathlib import Path

from photo_feed.errors import PhotoFeedError
from photo_feed.google_photos import fetch_html, parse_shared_album_html

FIXTURE = Path(__file__).parent / "fixtures" / "google_share_page.html"


class ParseSharedAlbumTests(unittest.TestCase):
    def test_fixture_page_lists_photo_and_video(self):
        listing = parse_shared_album_html(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(listing.album_id, "fixture-album")
        self.assertEqual(listing.title, "Picnic")
        self.assertFalse(listing.truncated)
        self.assertEqual(
            [item.as_dict() for item in listing.items],
            [
                {
                    "id": "fixture-photo-1",
                    "filename": "picnic.jpg",
                    "kind": "photo",
                    "url": "https://cdn.example.test/picnic.jpg",
                    "width": 800,
                    "height": 600,
                    "created_at": "2023-11-14T22:13:20Z",
                    "added_at": "2023-11-15T22:13:20Z",
                    "size_bytes": 2048,
                },
                {
                    "id": "fixture-video-1",
                    "filename": "clip.mp4",
                    "kind": "video",
                    "url": "https://cdn.example.test/clip.mp4",
                    "width": 1920,
                    "height": 1080,
                    "created_at": "2023-11-14T23:13:20Z",
                    "added_at": "2023-11-15T22:13:20Z",
                    "size_bytes": None,
                },
            ],
        )

    def test_continuation_token_marks_the_list_as_truncated(self):
        html = """
        <script>AF_initDataCallback({key: 'ds:1', hash: '1', data:[null,[
          ["only",["https://cdn.example.test/one.jpg",10,10],1700000000000,"t",0,1700086400000]
        ],"more-items",["alb","Day"]], sideChannel: {}});</script>
        """
        listing = parse_shared_album_html(html)
        self.assertTrue(listing.truncated)
        self.assertEqual(listing.title, "Day")
        self.assertEqual(len(listing.items), 1)

    def test_function_return_wrapper_is_parsed(self):
        html = """
        AF_initDataCallback({key: 'ds:1', hash: '1', data:function(){return [null,[
          ["wrapped",["https://cdn.example.test/wrapped.jpg",4,5],1700000000000,"t",0,1700086400000]
        ],"",["alb","Wrapped"]]}, sideChannel: {}});
        """
        listing = parse_shared_album_html(html)
        self.assertEqual(listing.items[0].id, "wrapped")
        self.assertEqual(listing.title, "Wrapped")

    def test_plain_image_url_fallback_uses_a_direct_file_link(self):
        # Token is made up. It is not a photo from anyone's album.
        html = "<html>https://lh3.googleusercontent.com/pw/synthetic-fixture-token=w100-h100</html>"
        listing = parse_shared_album_html(html)
        self.assertEqual(len(listing.items), 1)
        item = listing.items[0]
        self.assertEqual(item.kind, "photo")
        self.assertEqual(
            item.url,
            "https://lh3.googleusercontent.com/pw/synthetic-fixture-token=d",
        )
        self.assertTrue(item.id)

    def test_empty_page_explains_link_sharing(self):
        with self.assertRaises(PhotoFeedError) as caught:
            parse_shared_album_html("<html><body>Sign in to Google Photos</body></html>")
        message = str(caught.exception)
        self.assertIn("Create link", message)
        self.assertNotIn("Sign in to Google Photos", message)

    def test_fetch_html_reads_the_response_body(self):
        seen = {}

        class Response:
            status = 200

            def read(self):
                return b"<html>ok</html>"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def open_url(request, timeout):
            seen["url"] = request.full_url
            seen["timeout"] = timeout
            seen["user_agent"] = request.get_header("User-agent")
            return Response()

        body = fetch_html("https://photos.app.goo.gl/example", open_url=open_url, timeout=5)
        self.assertEqual(body, "<html>ok</html>")
        self.assertEqual(seen["url"], "https://photos.app.goo.gl/example")
        self.assertEqual(seen["timeout"], 5)
        self.assertIn("Mozilla", seen["user_agent"])

    def test_fetch_html_turns_http_errors_into_a_short_message(self):
        class Response:
            status = 404

            def read(self):
                return b"secret page body"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def open_url(request, timeout):
            return Response()

        with self.assertRaises(PhotoFeedError) as caught:
            fetch_html("https://photos.app.goo.gl/missing", open_url=open_url)
        self.assertIn("404", str(caught.exception))
        self.assertNotIn("secret page body", str(caught.exception))

    def test_fetch_html_unzips_gzip(self):
        payload = b"<html>plain page</html>"

        class Response:
            status = 200
            headers = {"Content-Encoding": "gzip"}

            def read(self):
                return gzip.compress(payload)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def open_url(request, timeout):
            self.assertIn("gzip", request.get_header("Accept-encoding").lower())
            return Response()

        body = fetch_html("https://photos.app.goo.gl/example", open_url=open_url)
        self.assertEqual(body, payload.decode("utf-8"))

    def test_fetch_html_refuses_brotli_without_echoing_the_body(self):
        class Response:
            status = 200
            headers = {"Content-Encoding": "br"}

            def read(self):
                return b"compressed-album-body"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with self.assertRaises(PhotoFeedError) as caught:
            fetch_html("https://photos.app.goo.gl/example", open_url=lambda request, timeout: Response())
        self.assertNotIn("compressed-album-body", str(caught.exception))
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from photo_feed.google_photos import parse_album_html, parse_photo_html

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ALBUM_URL = "https://photos.google.com/share/FixtureAlbum?key=fixture-key"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ParseAlbumHtmlTest(unittest.TestCase):
    def test_structured_page_returns_photo_and_video(self):
        parsed = parse_album_html(read_fixture("google_album.html"), ALBUM_URL)

        self.assertEqual(parsed.title, "Fixture Picnic & Games")
        self.assertEqual(parsed.photo_pages, [])
        self.assertEqual([item["id"] for item in parsed.items], ["fixture-photo-1", "fixture-video-1"])

        photo = parsed.items[0]
        self.assertEqual(photo["kind"], "image")
        self.assertEqual(photo["filename"], "fixture-photo-1.jpg")
        self.assertEqual(photo["url"], "https://lh3.googleusercontent.com/pw/FIXTURE_PHOTO_ONE=s2048")
        self.assertEqual(photo["original_url"], "https://lh3.googleusercontent.com/pw/FIXTURE_PHOTO_ONE=d")
        self.assertEqual(photo["width"], 800)
        self.assertEqual(photo["height"], 600)
        self.assertEqual(photo["date"], "2024-03-09T16:00:00Z")
        self.assertIsNone(photo["size_bytes"])

        video = parsed.items[1]
        self.assertEqual(video["kind"], "video")
        self.assertEqual(video["filename"], "fixture-video-1.mp4")
        self.assertEqual(video["url"], "https://lh3.googleusercontent.com/pw/FIXTURE_VIDEO_ONE=s2048")
        self.assertEqual(video["original_url"], "https://lh3.googleusercontent.com/pw/FIXTURE_VIDEO_ONE=d")
        self.assertEqual(video["width"], 1920)
        self.assertEqual(video["height"], 1080)
        self.assertEqual(video["date"], "2024-03-09T16:00:02Z")
        self.assertFalse(parsed.partial)

    def test_a_continuation_token_marks_the_batch_partial(self):
        html = """
        <html><head><meta property="og:title" content="Fixture More"></head>
        <script>AF_initDataCallback({key: 'ds:0', hash: '1', data:[null, [
          ["fixture-photo-1", ["https://lh3.googleusercontent.com/pw/FIXTURE_PHOTO_ONE", 10, 10], 1710000000000]
        ], "FIXTURE_NEXT_PAGE_TOKEN_NOT_REAL_123456"], sideChannel: {}});</script>
        </html>
        """
        parsed = parse_album_html(html, ALBUM_URL)
        self.assertEqual(len(parsed.items), 1)
        self.assertTrue(parsed.partial)

    def test_links_only_page_keeps_photo_pages_and_skips_cover(self):
        parsed = parse_album_html(read_fixture("google_album_links_only.html"), ALBUM_URL)

        self.assertEqual(parsed.title, "Fixture Links Album")
        self.assertEqual(parsed.items, [])
        self.assertEqual(parsed.photo_pages, [
            "https://photos.google.com/share/FixtureAlbum/photo/FixturePhotoA?key=fixture-key",
            "https://photos.google.com/share/FixtureAlbum/photo/FixturePhotoB?key=fixture-key",
        ])
        self.assertFalse(parsed.sign_in_required)
        joined = " ".join(parsed.photo_pages)
        self.assertNotIn("FIXTURE_COVER", joined)

    def test_loose_url_is_used_when_the_page_has_no_items_or_links(self):
        parsed = parse_album_html(read_fixture("google_loose_url.html"), ALBUM_URL)

        self.assertEqual(len(parsed.items), 1)
        self.assertEqual(parsed.items[0]["id"], "FIXTURE_LOOSE_URL")
        self.assertEqual(parsed.items[0]["kind"], "image")
        self.assertEqual(parsed.photo_pages, [])

    def test_sign_in_page_is_flagged(self):
        parsed = parse_album_html(read_fixture("google_sign_in.html"), ALBUM_URL)

        self.assertTrue(parsed.sign_in_required)
        self.assertEqual(parsed.items, [])
        self.assertEqual(parsed.photo_pages, [])

    def test_photo_page_parser_reads_one_item(self):
        item = parse_photo_html(
            read_fixture("google_photo_page_a.html"),
            "https://photos.google.com/share/FixtureAlbum/photo/FixturePhotoA?key=fixture-key",
        )

        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item["id"], "fixture-photo-a")
        self.assertEqual(item["width"], 640)
        self.assertEqual(item["url"], "https://lh3.googleusercontent.com/pw/FIXTURE_PAGE_A=s2048")


if __name__ == "__main__":
    unittest.main()
