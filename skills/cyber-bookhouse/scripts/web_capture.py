#!/usr/bin/env python3
"""Capture readable evidence from a public webpage without browser cookies."""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import re
import socket
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, getproxies


MAX_BYTES = 8 * 1024 * 1024
SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}
CONTENT_HINT = re.compile(r"article|content|entry|main|post|story", re.I)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(value.rstrip() + "\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def atomic_json(path: Path, payload: dict) -> None:
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP or HTTPS URLs are supported.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not supported.")
    hostname = parsed.hostname.rstrip(".").lower()
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        raise ValueError("Local and private network addresses are not supported.")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        raise ValueError("Local and private network addresses are not supported.")
    proxies = getproxies()
    if proxies.get(parsed.scheme) or proxies.get("all"):
        return
    try:
        default_port = 443 if parsed.scheme == "https" else 80
        addresses = socket.getaddrinfo(hostname, parsed.port or default_port)
    except socket.gaierror as exc:
        raise ValueError("The URL host could not be resolved.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Local and private network addresses are not supported.")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ReadableHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.article_parts: list[str] = []
        self.metadata: dict[str, str] = {}
        self._title_depth = 0
        self._body_depth = 0
        self._content_depth = 0
        self._skip_depth = 0
        self._stack: list[tuple[str, bool, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        lowered = tag.lower()
        if lowered == "meta":
            key = (
                values.get("property")
                or values.get("name")
                or values.get("itemprop")
            ).lower()
            content = values.get("content", "").strip()
            if key and content:
                self.metadata.setdefault(key, content)
            return
        skipped = lowered in SKIP_TAGS
        hint = " ".join((values.get("class", ""), values.get("id", "")))
        content_root = bool(
            lowered in {"article", "main"} or CONTENT_HINT.search(hint)
        )
        self._stack.append((lowered, skipped, content_root))
        if skipped:
            self._skip_depth += 1
            return
        if lowered == "title":
            self._title_depth += 1
        if lowered == "body":
            self._body_depth += 1
        if content_root:
            self._content_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        matched: tuple[str, bool, bool] | None = None
        while self._stack:
            item = self._stack.pop()
            if item[1] and self._skip_depth:
                self._skip_depth -= 1
            if item[2] and self._content_depth:
                self._content_depth -= 1
            if item[0] == lowered:
                matched = item
                break
        if matched and matched[1]:
            return
        if lowered == "title" and self._title_depth:
            self._title_depth -= 1
        if lowered == "body" and self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if not value:
            return
        if self._title_depth:
            self.title_parts.append(value)
        if self._body_depth:
            self.body_parts.append(value)
        if self._content_depth:
            self.article_parts.append(value)

    def readable_text(self) -> str:
        selected = self.article_parts if self.has_structured_content() else self.body_parts
        output: list[str] = []
        for value in selected:
            if not output or output[-1] != value:
                output.append(value)
        return "\n\n".join(output)

    def has_structured_content(self) -> bool:
        return len(" ".join(self.article_parts)) >= 160

    def title(self) -> str:
        for key in ("og:title", "twitter:title"):
            if self.metadata.get(key):
                return self.metadata[key]
        return " ".join(self.title_parts).strip()


def fetch(url: str) -> tuple[str, str, str]:
    validate_public_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; cyber-bookhouse/0.2.7; public-page-reader)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    with build_opener(SafeRedirect()).open(request, timeout=30) as response:
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read(MAX_BYTES + 1)
        final_url = response.geturl()
    if len(raw) > MAX_BYTES:
        raise ValueError("The page is larger than the 8 MB capture limit.")
    if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
        raise ValueError(f"Unsupported public page content type: {content_type}")
    return raw.decode(charset, errors="replace"), content_type, final_url


def capture(args: argparse.Namespace) -> tuple[dict, int]:
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.staged_text:
        text = Path(args.staged_text).expanduser().read_text(
            encoding="utf-8", errors="replace"
        ).strip()
        if len(text) < 80:
            raise ValueError("The staged visible page text is too short to verify.")
        title = args.title or "Visible page capture"
        method = "authorized_browser"
        final_url = args.url
        metadata: dict[str, str] = {}
        structured = True
    else:
        source, content_type, final_url = fetch(args.url)
        method = "public_page"
        metadata = {"content_type": content_type}
        if content_type == "text/plain":
            text = source.strip()
            title = args.title or urlparse(final_url).path.rsplit("/", 1)[-1] or final_url
            structured = True
        else:
            parser = ReadableHTML()
            parser.feed(source)
            text = parser.readable_text()
            title = args.title or parser.title() or final_url
            structured = parser.has_structured_content()
            for source_key, target_key in (
                ("author", "author"),
                ("article:author", "author"),
                ("article:published_time", "published_at"),
                ("date", "published_at"),
                ("description", "description"),
                ("og:description", "description"),
            ):
                if parser.metadata.get(source_key) and target_key not in metadata:
                    metadata[target_key] = parser.metadata[source_key]
    length = len(text)
    if length >= 400 and structured:
        status = "full_text"
    elif length >= 80:
        status = "partial"
    else:
        status = "metadata_only"
    page = f"# {title}\n\n> 来源：{final_url}\n\n{text}".rstrip()
    atomic_text(output / "content.md", page)
    receipt = {
        "source_url": args.url,
        "final_url": final_url,
        "captured_at": now(),
        "status": "complete" if status == "full_text" else "partial",
        "content_status": status,
        "acquisition_method": method,
        "title": title,
        "content_path": str(output / "content.md"),
        "character_count": length,
        "metadata": metadata,
        "structured_content": structured,
    }
    atomic_json(output / "receipt.json", receipt)
    return receipt, 0 if length >= 80 else 3


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("url")
    value.add_argument("--output-dir", required=True)
    value.add_argument("--staged-text", help="Visible page text exported after user authorization.")
    value.add_argument("--title", help="Optional title for staged visible text.")
    return value


def main() -> int:
    try:
        receipt, code = capture(parser().parse_args())
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
