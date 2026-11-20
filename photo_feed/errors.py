"""Errors a person can read. Messages stay short and leave album contents out."""


class PhotoFeedError(Exception):
    """The album could not be read. The message is safe to show to a person or a bot."""
"""Plain-language errors a person can act on."""


class AlbumError(Exception):
    """A problem with the album link or the local setup.

    The message is safe to show. It should not include page HTML or photo URLs.
    """
