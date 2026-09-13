"""Ordinary HTTPS download of PSP's publicly published national export."""

import asyncio
from dataclasses import dataclass

import aiohttp

from .api import SourceError
from .const import MAX_CSV_BYTES, PSP_EXPORT_URL


@dataclass
class CSVDownload:
    body: bytes | None
    etag: str | None
    last_modified: str | None


class OpenDataClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def fetch(self, etag=None, last_modified=None):
        headers = {"Accept": "text/csv, application/octet-stream;q=0.9"}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        try:
            async with asyncio.timeout(45):
                async with self.session.get(PSP_EXPORT_URL, headers=headers, allow_redirects=False) as response:
                    if response.status == 304:
                        return CSVDownload(None, response.headers.get("ETag"), response.headers.get("Last-Modified"))
                    if response.status != 200:
                        raise SourceError(f"Eksport CSV PSP: HTTP {response.status}")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        body.extend(chunk)
                        if len(body) > MAX_CSV_BYTES:
                            raise SourceError("Eksport CSV PSP przekracza 32 MiB")
                    return CSVDownload(bytes(body), response.headers.get("ETag"), response.headers.get("Last-Modified"))
        except TimeoutError as err:
            raise SourceError("Przekroczono czas pobierania pełnego eksportu CSV PSP (45 s)") from err
        except aiohttp.ClientError as err:
            raise SourceError("Nie udało się połączyć z publicznym eksportem CSV PSP") from err
