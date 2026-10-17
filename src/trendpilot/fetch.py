"""Fetch a public page. Private and local addresses are refused."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

MAX_CHARS = 7000
MAX_BYTES = 400_000


class FetchError(RuntimeError):
    pass


def fetch_page(url: str) -> str:
    final_url = _assert_public(url)
    headers = {
        "User-Agent": "TrendPilot/0.1 (public-page research for a local business demo)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
    }
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
            response = client.get(final_url)
            _assert_public(str(response.url))
            response.raise_for_status()
            raw = response.content[:MAX_BYTES]
            content_type = response.headers.get("content-type", "")
    except FetchError:
        raise
    except httpx.HTTPError as exc:
        raise FetchError(f"Could not open {final_url}: {exc}") from exc

    if "html" in content_type or raw.lstrip()[:1] == b"<":
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "form"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = soup.get_text("\n", strip=True)
        body = f"URL: {final_url}\nTITLE: {title}\n\n{text}"
    else:
        body = f"URL: {final_url}\n\n{raw.decode('utf-8', errors='replace')}"

    if len(body) > MAX_CHARS:
        body = body[:MAX_CHARS] + "\n[truncated]"
    return body


def _assert_public(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise FetchError("Only public http(s) URLs are allowed.")
    host = parsed.hostname.strip("[]")
    if host.lower() in {"localhost", "localhost.localdomain"} or host.lower().endswith(".local"):
        raise FetchError("Local addresses are blocked.")
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise FetchError(f"Could not resolve {host}") from exc
        addresses = [item[4][0] for item in infos]
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_reserved,
                ip.is_multicast,
                ip.is_unspecified,
            )
        ):
            raise FetchError("Private or local addresses are blocked.")
    return parsed.geturl()
