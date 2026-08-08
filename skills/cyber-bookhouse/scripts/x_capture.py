#!/usr/bin/env python3
"""Capture a public X post or X Article without account or browser state."""

from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import math
import os
import re
import socket
import sys
import tempfile
import time
from datetime import datetime, timezone
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
    getproxies,
)


VERSION = "0.2.7"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150 Safari/537.36 "
    f"cyber-bookhouse/{VERSION}"
)
MAX_PAGE_BYTES = 16 * 1024 * 1024
MAX_STATUS_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 80 * 1024 * 1024
MAX_IMAGES = 30
MAX_IMAGE_TOTAL_BYTES = 400 * 1024 * 1024
MAX_IMAGE_TOTAL_SECONDS = 300.0
X_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}
X_MEDIA_HOSTS = {"pbs.twimg.com"}
X_NETWORK_HOSTS = X_HOSTS | X_MEDIA_HOSTS | {
    "abs.twimg.com",
    "api.x.com",
    "cdn.syndication.twimg.com",
}
X_STATUS_PATH = re.compile(r"^/(?:[^/]+/)?status/(\d+)(?:/.*)?$")
X_ARTICLE_PATH = re.compile(r"^/i/article/(\d+)(?:/.*)?$")
SHORTLINK = re.compile(r"https?://t\.co/[A-Za-z0-9]+")
AUTH_PROMPT = re.compile(
    r"\b(?:log\s*in|sign\s*up)(?:\s+(?:to|for)\s+(?:x|twitter))?\b"
    r"|this browser is no longer supported"
    r"|javascript is not available",
    re.IGNORECASE,
)


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


def validate_https_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Only public HTTPS URLs are supported.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not supported.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The URL contains an invalid port.") from exc
    if port not in {None, 443}:
        raise ValueError("Custom URL ports are not supported.")
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
    if not (getproxies().get(parsed.scheme) or getproxies().get("all")):
        try:
            addresses = socket.getaddrinfo(hostname, 443)
        except socket.gaierror as exc:
            raise ValueError("The URL host could not be resolved.") from exc
        for address in addresses:
            if not ipaddress.ip_address(address[4][0]).is_global:
                raise ValueError(
                    "Local and private network addresses are not supported."
                )
    return urlunparse(parsed._replace(netloc=hostname))


def parse_status_url(raw_url: str) -> tuple[str, str]:
    shaped = validate_https_url(raw_url)
    parsed = urlparse(shaped)
    if (parsed.hostname or "").lower() not in X_HOSTS:
        raise ValueError("Only x.com or twitter.com status URLs are supported.")
    match = X_STATUS_PATH.fullmatch(parsed.path)
    if not match:
        raise ValueError("The URL is not a recognizable X status URL.")
    status_id = match.group(1)
    canonical = urlunparse(
        parsed._replace(
            scheme="https",
            netloc="x.com",
            path=f"/i/status/{status_id}",
            params="",
            query="",
            fragment="",
        )
    )
    return status_id, canonical


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        shaped = validate_https_url(newurl)
        if (urlparse(shaped).hostname or "").lower() not in X_NETWORK_HOSTS:
            raise ValueError("Redirect left the official X HTTPS hosts.")
        return super().redirect_request(req, fp, code, msg, headers, shaped)


class AllowedHostsRedirect(SafeRedirect):
    def __init__(self, allowed_hosts: set[str]) -> None:
        super().__init__()
        self.allowed_hosts = {item.lower() for item in allowed_hosts}

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        shaped = validate_https_url(newurl)
        parsed = urlparse(shaped)
        if (parsed.hostname or "").lower() not in self.allowed_hosts:
            raise ValueError("Redirect left the allowed HTTPS media hosts.")
        return super().redirect_request(req, fp, code, msg, headers, shaped)


OPENER = build_opener(SafeRedirect())


class DownloadSizeLimitExceeded(ValueError):
    pass


class DownloadDeadlineExceeded(TimeoutError):
    pass


class UnsupportedImageType(ValueError):
    pass


class IncompleteImage(ValueError):
    pass


def request_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def bounded_read(response, limit: int) -> bytes:
    length = response.headers.get("Content-Length")
    if length:
        try:
            if int(length) > limit:
                raise ValueError(f"Response exceeds byte limit: {limit}")
        except ValueError:
            if str(length).isdigit():
                raise
    try:
        data = response.read(limit + 1)
    except IncompleteRead as exc:
        data = exc.partial
    if len(data) > limit:
        raise ValueError(f"Response exceeds byte limit: {limit}")
    return data


def fetch_bytes(
    url: str, *, limit: int = MAX_PAGE_BYTES, referer: str | None = None
) -> tuple[bytes, str, dict[str, str]]:
    validate_https_url(url)
    for attempt, delay in enumerate((0, 1, 3), start=1):
        if delay:
            time.sleep(delay)
        request = Request(url, headers=request_headers(referer))
        try:
            with OPENER.open(request, timeout=40) as response:
                data = bounded_read(response, limit)
                if not data and attempt < 3:
                    continue
                headers = {
                    key.lower(): value for key, value in response.headers.items()
                }
                return data, response.geturl(), headers
        except HTTPError as exc:
            if exc.code not in {429, 503, 504} or attempt == 3:
                raise
    raise ValueError("Public request retry budget exhausted.")


def x_request_bytes(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    limit: int = MAX_PAGE_BYTES,
    referer: str | None = None,
) -> tuple[bytes, str, dict[str, str]]:
    """Make a bounded X request without forwarding guest headers on redirects."""
    validate_https_url(url)
    public_headers = request_headers(referer)
    sensitive: dict[str, str] = {}
    for key, value in (headers or {}).items():
        if key.lower() in {"authorization", "x-guest-token"}:
            sensitive[key] = value
        else:
            public_headers[key] = value
    for attempt, delay in enumerate((0, 1, 3), start=1):
        if delay:
            time.sleep(delay)
        request = Request(url, data=data, headers=public_headers, method=method)
        for key, value in sensitive.items():
            request.add_unredirected_header(key, value)
        try:
            with OPENER.open(request, timeout=40) as response:
                payload = bounded_read(response, limit)
                if not payload and attempt < 3:
                    continue
                response_headers = {
                    key.lower(): value for key, value in response.headers.items()
                }
                return payload, response.geturl(), response_headers
        except HTTPError as exc:
            if exc.code not in {429, 503, 504} or attempt == 3:
                raise
    raise ValueError("X request retry budget exhausted.")


def base36(value: float) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    integer = int(value)
    fraction = value - integer
    digits = "0" if integer == 0 else ""
    while integer:
        integer, remainder = divmod(integer, 36)
        digits = alphabet[remainder] + digits
    if fraction:
        digits += "."
        for _ in range(16):
            fraction *= 36
            digit = int(fraction)
            digits += alphabet[digit]
            fraction -= digit
            if fraction == 0:
                break
    return digits


def syndication_token(status_id: str) -> str:
    value = (float(status_id) / 1e15) * math.pi
    return base36(value).replace("0", "").replace(".", "")


def fetch_x_status(status_id: str) -> dict:
    features = ";".join(
        [
            "tfw_timeline_list:",
            "tfw_follower_count_sunset:true",
            "tfw_tweet_edit_backend:on",
            "tfw_refsrc_session:on",
            "tfw_fosnr_soft_interventions_enabled:on",
            "tfw_show_birdwatch_pivots_enabled:on",
            "tfw_show_business_verified_badge:on",
            "tfw_duplicate_scribes_to_settings:on",
            "tfw_use_profile_image_shape_enabled:on",
            "tfw_show_blue_verified_badge:on",
            "tfw_legacy_timeline_sunset:true",
            "tfw_show_gov_verified_badge:on",
            "tfw_show_business_affiliate_badge:on",
            "tfw_tweet_edit_frontend:on",
        ]
    )
    endpoint = "https://cdn.syndication.twimg.com/tweet-result?" + urlencode(
        {
            "id": status_id,
            "lang": "en",
            "features": features,
            "token": syndication_token(status_id),
        }
    )
    try:
        data, _, _ = fetch_bytes(endpoint, limit=MAX_STATUS_BYTES)
        payload = json.loads(data.decode("utf-8"))
    except Exception:
        raise ValueError(
            "X status is unavailable, deleted, restricted, or private."
        ) from None
    if not isinstance(payload, dict) or payload.get("__typename") == "TweetTombstone":
        raise ValueError("X status is unavailable, deleted, restricted, or private.")
    returned_id = str(payload.get("id_str") or payload.get("id") or "").strip()
    if returned_id != status_id:
        raise ValueError("X status identity did not match the requested URL.")
    return payload


def nested_value(value: object, keys: tuple[str, ...]) -> object:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def x_full_text(tweet: dict) -> str:
    note_text = nested_value(
        tweet, ("note_tweet", "note_tweet_results", "result", "text")
    )
    if isinstance(note_text, str) and note_text.strip():
        return html.unescape(note_text.strip())
    return html.unescape(str(tweet.get("text") or "").strip())


def x_article_reference(tweet: dict) -> dict | None:
    raw_article = tweet.get("article")
    article = raw_article if isinstance(raw_article, dict) else {}
    nested_article = nested_value(article, ("article_results", "result"))
    if isinstance(nested_article, dict):
        article = nested_article
    article_id = str(
        article.get("rest_id")
        or article.get("id_str")
        or article.get("id")
        or ""
    ).strip()
    article_url = ""
    entities = tweet.get("entities") or {}
    for entity in entities.get("urls") or []:
        if not isinstance(entity, dict):
            continue
        for key in ("expanded_url", "unwound_url", "url"):
            candidate = html.unescape(str(entity.get(key) or "").strip())
            parsed = urlparse(candidate)
            match = X_ARTICLE_PATH.fullmatch(parsed.path)
            if (
                match
                and (parsed.hostname or "").lower() in X_HOSTS
                and parsed.scheme.lower() in {"http", "https"}
            ):
                if article_id and article_id != match.group(1):
                    raise ValueError(
                        "X_ARTICLE_BODY_UNAVAILABLE: article reference IDs did not match"
                    )
                article_id = article_id or match.group(1)
                article_url = f"https://x.com/i/article/{article_id}"
                break
        if article_url:
            break
    if not article and not article_url:
        return None
    if not article_id:
        raise ValueError(
            "X_ARTICLE_BODY_UNAVAILABLE: article reference has no stable identity"
        )
    if not article_url:
        article_url = f"https://x.com/i/article/{article_id}"
    return {
        "article_id": article_id,
        "article_url": article_url,
        "article_title": str(article.get("title") or "").strip(),
        "preview": str(
            article.get("preview_text") or article.get("preview") or ""
        ).strip(),
        "cover_media": article.get("cover_media"),
    }


def x_main_script_url(page: str, page_url: str) -> str:
    for match in re.finditer(
        r"<(?:script|link)\b[^>]*\b(?:src|href)\s*=\s*(['\"])(.*?)\1",
        page,
        re.IGNORECASE,
    ):
        source = html.unescape(match.group(2)).replace("\\/", "/")
        candidate = urljoin(page_url, source)
        parsed = urlparse(candidate)
        if (
            parsed.scheme.lower() == "https"
            and parsed.hostname == "abs.twimg.com"
            and parsed.port in {None, 443}
            and re.fullmatch(
                r"/responsive-web/client-web/main\.[A-Za-z0-9._-]+\.js",
                parsed.path,
            )
        ):
            return candidate
    raise ValueError("X web page has no current main bundle.")


def x_bundle_credentials(bundle: str) -> tuple[str, str]:
    normalized = (
        bundle.replace("\\u002F", "/")
        .replace("\\u003D", "=")
        .replace("\\x2F", "/")
        .replace("\\x3D", "=")
    )
    bearer = ""
    bearer_patterns = (
        r"Bearer\s+([A-Za-z0-9%._~+/=-]{60,300})",
        r"(['\"])(A{10,}[A-Za-z0-9%._~+/=-]{50,290})\1",
    )
    for pattern in bearer_patterns:
        for match in re.finditer(pattern, normalized):
            candidate = match.group(match.lastindex or 1)
            if re.fullmatch(r"[A-Za-z0-9%._~+/=-]{60,300}", candidate):
                bearer = candidate
                break
        if bearer:
            break
    query_id = ""
    query_patterns = (
        r"queryId\s*:\s*['\"]([A-Za-z0-9_-]{8,128})['\"][^{}]{0,600}"
        r"operationName\s*:\s*['\"]TweetResultByRestId['\"]",
        r"operationName\s*:\s*['\"]TweetResultByRestId['\"][^{}]{0,600}"
        r"queryId\s*:\s*['\"]([A-Za-z0-9_-]{8,128})['\"]",
        r"['\"]TweetResultByRestId['\"]\s*:\s*['\"]"
        r"([A-Za-z0-9_-]{8,128})['\"]",
    )
    for pattern in query_patterns:
        match = re.search(pattern, normalized)
        if match:
            query_id = match.group(1)
            break
    if not bearer or not query_id:
        raise ValueError("X web bundle has no public guest route.")
    return bearer, query_id


def x_public_web_credentials(article_url: str) -> tuple[str, str]:
    for page_url in ("https://x.com/home", article_url):
        try:
            page_bytes, final_url, _ = fetch_bytes(page_url)
            main_url = x_main_script_url(
                page_bytes.decode("utf-8", errors="replace"), final_url
            )
            bundle_bytes, _, _ = fetch_bytes(
                main_url, limit=MAX_PAGE_BYTES, referer=final_url
            )
            return x_bundle_credentials(
                bundle_bytes.decode("utf-8", errors="replace")
            )
        except Exception:
            continue
    raise ValueError("X public guest route is unavailable.")


X_ARTICLE_FEATURES = {
    "articles_preview_enabled": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "view_counts_everywhere_api_enabled": True,
}
X_ARTICLE_FIELD_TOGGLES = {
    "withArticlePlainText": True,
    "withArticleRichContentState": True,
    "withDisallowedReplyControls": False,
    "withGrokAnalyze": False,
}


def x_article_result_from_graphql(payload: dict, status_id: str) -> dict:
    result = nested_value(payload, ("data", "tweetResult", "result"))
    for _ in range(4):
        if not isinstance(result, dict):
            break
        wrapped = result.get("tweet")
        if isinstance(wrapped, dict) and not isinstance(result.get("article"), dict):
            result = wrapped
            continue
        break
    if not isinstance(result, dict):
        raise ValueError("X Article result is missing.")
    returned_status_id = str(
        result.get("rest_id") or result.get("id_str") or ""
    ).strip()
    if not returned_status_id or returned_status_id != status_id:
        raise ValueError("X status identity did not match the GraphQL result.")
    article = result.get("article")
    article_result = nested_value(article, ("article_results", "result"))
    if not isinstance(article_result, dict):
        raise ValueError("X Article result is missing.")
    return article_result


def fetch_x_article_public(status_id: str, article_url: str) -> dict:
    try:
        bearer, query_id = x_public_web_credentials(article_url)
        activation, _, _ = x_request_bytes(
            "https://api.x.com/1.1/guest/activate.json",
            method="POST",
            headers={
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            data=b"",
            limit=1024 * 1024,
            referer="https://x.com/home",
        )
        guest_token = str(
            json.loads(activation.decode("utf-8")).get("guest_token") or ""
        ).strip()
        if not guest_token:
            raise ValueError("X guest activation returned no token.")
        variables = {
            "tweetId": status_id,
            "withCommunity": False,
            "includePromotedContent": False,
            "withVoice": False,
        }
        endpoint = (
            f"https://x.com/i/api/graphql/{quote(query_id, safe='')}"
            "/TweetResultByRestId?"
            + urlencode(
                {
                    "variables": json.dumps(variables, separators=(",", ":")),
                    "features": json.dumps(
                        X_ARTICLE_FEATURES, separators=(",", ":")
                    ),
                    "fieldToggles": json.dumps(
                        X_ARTICLE_FIELD_TOGGLES, separators=(",", ":")
                    ),
                }
            )
        )
        graph, _, _ = x_request_bytes(
            endpoint,
            headers={
                "Authorization": f"Bearer {bearer}",
                "X-Guest-Token": guest_token,
                "X-Twitter-Active-User": "yes",
                "X-Twitter-Client-Language": "en",
            },
            limit=MAX_PAGE_BYTES,
            referer=article_url,
        )
        article = x_article_result_from_graphql(
            json.loads(graph.decode("utf-8")), status_id
        )
        if not str(article.get("plain_text") or "").strip() and not x_article_blocks(
            article.get("content_state")
        ):
            raise ValueError("X Article body is missing.")
        return article
    except Exception:
        raise ValueError(
            "X_ARTICLE_BODY_UNAVAILABLE: public X guest route returned no full body"
        ) from None


def x_article_blocks(content_state: object) -> list[dict]:
    if isinstance(content_state, str):
        try:
            content_state = json.loads(content_state)
        except json.JSONDecodeError:
            return []
    if not isinstance(content_state, dict):
        return []
    return [
        item for item in content_state.get("blocks") or [] if isinstance(item, dict)
    ]


def recursive_values(value: object, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, (str, int)):
                text = str(item).strip()
                if text:
                    found.append(text)
            elif isinstance(item, (dict, list)):
                found.extend(recursive_values(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(recursive_values(item, keys))
    return found


def x_media_url(media: object) -> str:
    for key in (
        "original_img_url",
        "original_image_url",
        "media_url_https",
        "media_url",
    ):
        values = recursive_values(media, {key})
        if values:
            url = values[0]
            break
    else:
        return ""
    parsed = urlparse(url)
    if parsed.hostname == "pbs.twimg.com" and "/media/" in parsed.path:
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["name"] = "orig"
        url = urlunparse(parsed._replace(query=urlencode(query)))
    return url


def validate_x_media_url(raw_url: str) -> str:
    shaped = validate_https_url(raw_url)
    if (urlparse(shaped).hostname or "").lower() not in X_MEDIA_HOSTS:
        raise ValueError("X Article media host is not allowed.")
    return shaped


def x_media_ids(media: object) -> list[str]:
    return list(
        dict.fromkeys(
            recursive_values(
                media, {"media_id", "mediaId", "media_id_str", "id_str", "id"}
            )
        )
    )


def x_article_media_items(article: dict, hint: dict) -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    cover = article.get("cover_media") or hint.get("cover_media")
    if isinstance(cover, dict):
        items.append(("cover", cover))
    entities = article.get("media_entities") or []
    if isinstance(entities, dict):
        entities = [entities] if x_media_url(entities) else list(entities.values())
    for entity in entities:
        if isinstance(entity, dict):
            items.append(("article", entity))
    content_state = article.get("content_state")
    if isinstance(content_state, str):
        try:
            content_state = json.loads(content_state)
        except json.JSONDecodeError:
            content_state = {}
    if isinstance(content_state, dict):
        raw_entity_map = content_state.get("entityMap") or {}
        entity_values = (
            list(raw_entity_map.values())
            if isinstance(raw_entity_map, dict)
            else [
                item.get("value")
                for item in raw_entity_map
                if isinstance(item, dict)
            ]
            if isinstance(raw_entity_map, list)
            else []
        )
        for entity in entity_values:
            if isinstance(entity, dict) and x_media_url(entity):
                items.append(("article", entity))
    return items


def sniff_image_type(prefix: bytes) -> tuple[str, str]:
    if prefix.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if prefix.startswith((b"GIF87a", b"GIF89a")):
        return ".gif", "image/gif"
    if len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP":
        return ".webp", "image/webp"
    raise UnsupportedImageType(
        "X Article image is HTML, SVG, or an unsupported binary type."
    )


def image_file_is_complete(path: Path, extension: str, total: int) -> bool:
    with path.open("rb") as handle:
        prefix = handle.read(16)
        handle.seek(max(0, total - 16))
        suffix = handle.read()
    if extension == ".jpg":
        return suffix.endswith(b"\xff\xd9")
    if extension == ".png":
        return suffix.endswith(b"IEND\xaeB\x60\x82")
    if extension == ".gif":
        return suffix.endswith(b";")
    if extension == ".webp" and len(prefix) >= 12:
        declared_size = int.from_bytes(prefix[4:8], "little") + 8
        return prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP" and total == declared_size
    return False


def download_image(
    url: str,
    target_stem: Path,
    *,
    referer: str,
    limit: int,
    timeout: float,
    deadline: float,
) -> tuple[Path, dict]:
    shaped = validate_x_media_url(url)
    if timeout <= 0 or time.monotonic() >= deadline:
        raise DownloadDeadlineExceeded("Image download deadline exhausted.")
    opener = build_opener(AllowedHostsRedirect(X_MEDIA_HOSTS))
    target_stem.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_stem.with_suffix(".part")
    total = 0
    digest = hashlib.sha256()
    prefix = b""
    expected_total: int | None = None
    declared = ""
    try:
        temporary.unlink(missing_ok=True)
        for _attempt in range(8):
            if time.monotonic() >= deadline:
                raise DownloadDeadlineExceeded(
                    "Image download deadline exhausted."
                )
            headers = request_headers(referer)
            if total:
                headers["Range"] = f"bytes={total}-"
            request = Request(shaped, headers=headers)
            with opener.open(
                request, timeout=min(40.0, max(0.1, deadline - time.monotonic()))
            ) as response:
                response_status = int(getattr(response, "status", 200) or 200)
                content_range = response.headers.get("Content-Range", "")
                if total:
                    range_match = re.fullmatch(
                        r"bytes\s+(\d+)-(\d+)/(\d+)", content_range.strip()
                    )
                    if (
                        response_status != 206
                        or not range_match
                        or int(range_match.group(1)) != total
                    ):
                        raise IncompleteImage(
                            "X Article image server did not honor a safe byte range."
                        )
                    ranged_total = int(range_match.group(3))
                    if expected_total is not None and ranged_total != expected_total:
                        raise IncompleteImage(
                            "X Article image changed during download."
                        )
                    expected_total = ranged_total
                content_length = response.headers.get("Content-Length")
                if content_length and str(content_length).isdigit():
                    response_length = int(content_length)
                    if expected_total is None:
                        expected_total = total + response_length
                    if total + response_length > limit:
                        raise DownloadSizeLimitExceeded(
                            f"Image exceeds byte limit: {limit}"
                        )
                if expected_total is not None and expected_total > limit:
                    raise DownloadSizeLimitExceeded(
                        f"Image exceeds byte limit: {limit}"
                    )
                current_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                declared = declared or current_type
                if current_type in {
                    "text/html",
                    "image/svg+xml",
                    "text/xml",
                    "application/xml",
                }:
                    raise UnsupportedImageType(
                        "X Article image endpoint returned markup instead of an image."
                    )
                mode = "ab" if total else "wb"
                output = temporary.open(mode)
                try:
                    while True:
                        if time.monotonic() >= deadline:
                            raise DownloadDeadlineExceeded(
                                "Image download deadline exhausted."
                            )
                        incomplete = False
                        try:
                            chunk = response.read(1024 * 1024)
                        except IncompleteRead as exc:
                            chunk = exc.partial
                            incomplete = True
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > limit:
                            raise DownloadSizeLimitExceeded(
                                f"Image exceeds byte limit: {limit}"
                            )
                        if len(prefix) < 32:
                            prefix += chunk[: 32 - len(prefix)]
                        output.write(chunk)
                        digest.update(chunk)
                        if incomplete:
                            break
                finally:
                    output.close()
            if expected_total is not None and total < expected_total:
                continue
            extension, content_type = sniff_image_type(prefix)
            if image_file_is_complete(temporary, extension, total):
                break
            if expected_total is None:
                continue
            raise IncompleteImage("X Article image ended before its file trailer.")
        else:
            raise IncompleteImage("X Article image retry budget was exhausted.")
        target = target_stem.with_suffix(extension)
        os.replace(temporary, target)
        return target, {
            "filename": target.name,
            "relative_path": f"assets/{target.name}",
            "bytes": total,
            "sha256": digest.hexdigest(),
            "content_type": content_type,
            "source_url": shaped,
        }
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def image_failure_reason(exc: Exception, remaining_limit: int) -> str:
    if isinstance(exc, DownloadDeadlineExceeded):
        return "total_time_budget_exhausted"
    if isinstance(exc, TimeoutError):
        return "image_download_timeout"
    if isinstance(exc, URLError) and isinstance(
        getattr(exc, "reason", None), TimeoutError
    ):
        return "image_download_timeout"
    if isinstance(exc, DownloadSizeLimitExceeded):
        return (
            "total_byte_budget_exhausted"
            if remaining_limit < MAX_IMAGE_BYTES
            else "single_image_limit_exceeded"
        )
    if isinstance(exc, UnsupportedImageType):
        return "unsupported_image_type"
    if isinstance(exc, IncompleteImage):
        return "incomplete_image_download"
    if isinstance(exc, ValueError):
        return "image_url_rejected"
    return "image_download_failed"


def download_x_article_images(
    output: Path, source_url: str, article: dict, hint: dict
) -> tuple[list[dict], dict[str, str], dict]:
    records: list[dict] = []
    aliases: dict[str, str] = {}
    by_url: dict[str, dict] = {}
    downloaded_bytes = 0
    deadline = time.monotonic() + MAX_IMAGE_TOTAL_SECONDS
    incomplete_reason = ""
    media_items = x_article_media_items(article, hint)
    unique_urls = {url for _, media in media_items if (url := x_media_url(media))}
    missing_url_ids = [
        x_media_ids(media) for _, media in media_items if not x_media_url(media)
    ]
    for role, media in media_items:
        url = x_media_url(media)
        if not url:
            continue
        identifiers = x_media_ids(media)
        existing = by_url.get(url)
        if existing is not None:
            reference = f"assets/{existing['filename']}"
            for identifier in identifiers:
                aliases[identifier] = reference
            continue
        if len(records) >= MAX_IMAGES:
            incomplete_reason = "image_count_limit_reached"
            break
        remaining_limit = MAX_IMAGE_TOTAL_BYTES - downloaded_bytes
        if remaining_limit <= 0:
            incomplete_reason = "total_byte_budget_exhausted"
            break
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            incomplete_reason = "total_time_budget_exhausted"
            break
        per_image_limit = min(MAX_IMAGE_BYTES, remaining_limit)
        try:
            _, record = download_image(
                url,
                output / "assets" / f"image-{len(records) + 1:02d}",
                referer=source_url,
                limit=per_image_limit,
                timeout=remaining_seconds,
                deadline=deadline,
            )
        except Exception as exc:
            incomplete_reason = image_failure_reason(exc, per_image_limit)
            break
        record.update({"type": role, "media_ids": identifiers})
        records.append(record)
        downloaded_bytes += int(record["bytes"])
        by_url[url] = record
        reference = f"assets/{record['filename']}"
        aliases[url] = reference
        for identifier in identifiers:
            aliases[identifier] = reference
    if (
        not incomplete_reason
        and len(records) >= MAX_IMAGES
        and len(unique_urls) > len(records)
    ):
        incomplete_reason = "image_count_limit_reached"
    if not incomplete_reason and any(
        not identifiers
        or not any(identifier in aliases for identifier in identifiers)
        for identifiers in missing_url_ids
    ):
        incomplete_reason = "image_url_missing"
    return records, aliases, {
        "images_incomplete": bool(incomplete_reason),
        "images_incomplete_reason": incomplete_reason,
        "image_bytes_downloaded": downloaded_bytes,
    }


def atomic_media_references(
    block: dict, entity_map: dict, aliases: dict[str, str]
) -> list[str]:
    candidates = recursive_values(
        block.get("data") or {},
        {"media_id", "mediaId", "media_id_str", "id_str", "id"},
    )
    for entity_range in block.get("entityRanges") or []:
        if not isinstance(entity_range, dict):
            continue
        key = entity_range.get("key")
        entity = entity_map.get(str(key), entity_map.get(key))
        candidates.extend(
            recursive_values(
                entity or {},
                {
                    "media_id",
                    "mediaId",
                    "media_id_str",
                    "id_str",
                    "id",
                    "original_img_url",
                    "media_url_https",
                },
            )
        )
    return list(dict.fromkeys(aliases[item] for item in candidates if item in aliases))


def escape_markdown_text(value: str) -> str:
    escaped = re.sub(r"([\\`*_\[\]<>!|~^$%])", r"\\\1", value)
    lines: list[str] = []
    for line in escaped.splitlines():
        line = re.sub(
            r"^(\s{0,3})(#{1,6}|>|[-+](?=\s)|\d+[.)](?=\s)|={2,}\s*$|-{2,}\s*$)",
            lambda match: f"{match.group(1)}\\{match.group(2)}",
            line,
        )
        lines.append(line)
    return "\n".join(lines)


def fenced_code(lines: list[str]) -> list[str]:
    body = "\n".join(lines)
    longest = max((len(item) for item in re.findall(r"`+", body)), default=0)
    fence = "`" * max(3, longest + 1)
    return [fence, *lines, fence]


def draftjs_to_markdown(
    content_state: object, aliases: dict[str, str] | None = None
) -> str:
    if isinstance(content_state, str):
        try:
            content_state = json.loads(content_state)
        except json.JSONDecodeError:
            return ""
    if not isinstance(content_state, dict):
        return ""
    blocks = x_article_blocks(content_state)
    raw_entity_map = content_state.get("entityMap") or {}
    if isinstance(raw_entity_map, dict):
        entity_map = raw_entity_map
    elif isinstance(raw_entity_map, list):
        entity_map = {
            str(item.get("key")): item.get("value")
            for item in raw_entity_map
            if isinstance(item, dict)
            and item.get("key") is not None
            and isinstance(item.get("value"), dict)
        }
    else:
        entity_map = {}
    media_aliases = aliases or {}
    groups: list[tuple[str, list[str]]] = []
    code_lines: list[str] = []
    ordered_counts: dict[int, int] = {}
    previous_type = ""

    def add_group(kind: str, lines: list[str]) -> None:
        nonlocal code_lines
        if code_lines:
            groups.append(("code", fenced_code(code_lines)))
            code_lines = []
        if lines:
            groups.append((kind, lines))

    for block in blocks:
        block_type = str(block.get("type") or "unstyled")
        text = html.unescape(str(block.get("text") or "")).strip()
        safe_text = escape_markdown_text(text)
        try:
            depth = max(0, int(block.get("depth") or 0))
        except (TypeError, ValueError):
            depth = 0
        if block_type == "code-block":
            code_lines.append(text)
            previous_type = block_type
            continue
        if block_type == "atomic":
            references = atomic_media_references(
                block, entity_map, media_aliases
            )
            add_group(
                "paragraph",
                [f"![X Article 图片]({reference})" for reference in references],
            )
            previous_type = block_type
            continue
        if not text:
            if code_lines:
                add_group("paragraph", [])
            previous_type = block_type
            continue
        if block_type.startswith("header-"):
            levels = {
                "header-one": 2,
                "header-two": 3,
                "header-three": 4,
                "header-four": 5,
                "header-five": 6,
                "header-six": 6,
            }
            add_group(
                "paragraph", [f"{'#' * levels.get(block_type, 2)} {safe_text}"]
            )
        elif block_type == "blockquote":
            add_group(
                "paragraph", [f"> {line}" for line in safe_text.splitlines()]
            )
        elif block_type == "unordered-list-item":
            add_group("list", [f"{'  ' * depth}- {safe_text}"])
        elif block_type == "ordered-list-item":
            if previous_type != block_type:
                ordered_counts.clear()
            ordered_counts[depth] = ordered_counts.get(depth, 0) + 1
            for deeper in [item for item in ordered_counts if item > depth]:
                del ordered_counts[deeper]
            add_group(
                "list", [f"{'  ' * depth}{ordered_counts[depth]}. {safe_text}"]
            )
        else:
            add_group("paragraph", [safe_text])
        previous_type = block_type
    if code_lines:
        groups.append(("code", fenced_code(code_lines)))
    output: list[str] = []
    previous_kind = ""
    for kind, lines in groups:
        if output and not (kind == "list" and previous_kind == "list"):
            output.append("")
        output.extend(lines)
        previous_kind = kind
    return "\n".join(output).strip()


def has_unresolved_inline_media(
    content_state: object, aliases: dict[str, str]
) -> bool:
    if isinstance(content_state, str):
        try:
            content_state = json.loads(content_state)
        except json.JSONDecodeError:
            return False
    if not isinstance(content_state, dict):
        return False
    raw_entity_map = content_state.get("entityMap") or {}
    if isinstance(raw_entity_map, dict):
        entity_map = raw_entity_map
    elif isinstance(raw_entity_map, list):
        entity_map = {
            str(item.get("key")): item.get("value")
            for item in raw_entity_map
            if isinstance(item, dict)
            and item.get("key") is not None
            and isinstance(item.get("value"), dict)
        }
    else:
        entity_map = {}
    for block in x_article_blocks(content_state):
        if str(block.get("type") or "") != "atomic":
            continue
        media_entity = False
        for entity_range in block.get("entityRanges") or []:
            if not isinstance(entity_range, dict):
                continue
            key = entity_range.get("key")
            entity = entity_map.get(str(key), entity_map.get(key))
            entity_type = str((entity or {}).get("type") or "").upper()
            if "MEDIA" in entity_type or "IMAGE" in entity_type:
                media_entity = True
                break
        if media_entity and not atomic_media_references(block, entity_map, aliases):
            return True
    return False


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def validate_article_body(article: dict, hint: dict, tweet: dict) -> tuple[str, str]:
    plain_text = html.unescape(str(article.get("plain_text") or "").strip())
    blocks = x_article_blocks(article.get("content_state"))
    rich_text = normalized(
        " ".join(
            str(block.get("text") or "")
            for block in blocks
            if str(block.get("text") or "").strip()
        )
    )
    candidate = rich_text or normalized(plain_text)
    preview = normalized(str(hint.get("preview") or ""))
    tweet_text = normalized(x_full_text(tweet))
    tweet_shortlink = tweet_text if SHORTLINK.fullmatch(tweet_text) else ""
    prompt_like = bool(AUTH_PROMPT.search(candidate)) and len(candidate) <= max(
        500, len(preview) + 300
    )
    if (
        not candidate
        or candidate == preview
        or candidate == tweet_shortlink
        or SHORTLINK.fullmatch(candidate)
        or prompt_like
        or (preview and candidate.startswith(preview) and len(candidate) <= len(preview) + 32)
    ):
        raise ValueError(
            "X_ARTICLE_BODY_UNAVAILABLE: response contained only a preview or short link"
        )
    return plain_text, candidate


def author_name(tweet: dict) -> str:
    user = tweet.get("user") or {}
    name = str(user.get("name") or "").strip()
    handle = str(user.get("screen_name") or "").strip()
    if name and handle:
        return f"{name} (@{handle})"
    return name or (f"@{handle}" if handle else "")


def article_capture(
    output: Path,
    source_url: str,
    canonical_url: str,
    status_id: str,
    tweet: dict,
    hint: dict,
) -> dict:
    article_url = str(hint["article_url"])
    article = fetch_x_article_public(status_id, article_url)
    hinted_id = str(hint.get("article_id") or "").strip()
    result_id = str(article.get("rest_id") or "").strip()
    url_match = X_ARTICLE_PATH.fullmatch(urlparse(article_url).path)
    url_id = url_match.group(1) if url_match else ""
    if (
        not hinted_id
        or not result_id
        or not url_id
        or len({hinted_id, result_id, url_id}) != 1
    ):
        raise ValueError(
            "X_ARTICLE_BODY_UNAVAILABLE: article identity did not match the post"
        )
    plain_text, _ = validate_article_body(article, hint, tweet)
    images, aliases, image_status = download_x_article_images(
        output, source_url, article, hint
    )
    if (
        not image_status["images_incomplete"]
        and has_unresolved_inline_media(article.get("content_state"), aliases)
    ):
        image_status["images_incomplete"] = True
        image_status["images_incomplete_reason"] = "inline_image_unresolved"
    body = draftjs_to_markdown(
        article.get("content_state"), aliases
    ) or escape_markdown_text(plain_text)
    if not body.strip():
        raise ValueError(
            "X_ARTICLE_BODY_UNAVAILABLE: public X guest route returned no full body"
        )
    title = html.unescape(
        str(article.get("title") or hint.get("article_title") or "X Article").strip()
    )
    author = author_name(tweet)
    content = [
        f"# {escape_markdown_text(normalized(title))}",
        "",
        f"- 作者：{escape_markdown_text(normalized(author or '未知'))}",
        "- 发布时间："
        + escape_markdown_text(normalized(str(tweet.get("created_at") or "未知"))),
        f"- X 帖子：{canonical_url}",
        f"- 原文：{article_url}",
    ]
    cover = next((item for item in images if item.get("type") == "cover"), None)
    if cover:
        content.extend(["", f"![X Article 封面](assets/{cover['filename']})"])
    if image_status["images_incomplete"]:
        reason = image_status["images_incomplete_reason"]
        content.extend(
            [
                "",
                f"<!-- images_incomplete=true; reason={reason} -->",
                f"> [!WARNING] 图片采集不完整：{reason}",
            ]
        )
    content.extend(["", "## 正文", "", body])
    content_path = output / "content.md"
    atomic_text(content_path, "\n".join(content))
    receipt = {
        "source_url": source_url,
        "final_url": canonical_url,
        "captured_at": now(),
        "status": "partial" if image_status["images_incomplete"] else "complete",
        "content_status": "full_text",
        "acquisition_method": "x_public_guest",
        "platform": "x",
        "content_type": "article",
        "x_content_kind": "article",
        "title": title,
        "author": author,
        "published_at": str(tweet.get("created_at") or ""),
        "status_id": status_id,
        "article_id": result_id,
        "article_url": article_url,
        "content_path": str(content_path),
        "character_count": len(body),
        "structured_content": bool(x_article_blocks(article.get("content_state"))),
        "images": images,
        **image_status,
        "limitations": (
            [f"X Article images incomplete: {image_status['images_incomplete_reason']}"]
            if image_status["images_incomplete"]
            else []
        ),
    }
    atomic_json(output / "receipt.json", receipt)
    return receipt


def public_media_metadata(tweet: dict) -> list[dict]:
    records: list[dict] = []
    for item in tweet.get("mediaDetails") or []:
        if not isinstance(item, dict):
            continue
        media_type = str(item.get("type") or "").strip()
        original = item.get("original_info") or {}
        video_info = item.get("video_info") or {}
        records.append(
            {
                "type": media_type or "unknown",
                "width": original.get("width"),
                "height": original.get("height"),
                "duration_millis": video_info.get("duration_millis"),
            }
        )
    return records


def post_capture(
    output: Path,
    source_url: str,
    canonical_url: str,
    status_id: str,
    tweet: dict,
) -> dict:
    text = x_full_text(tweet)
    author = author_name(tweet)
    media = public_media_metadata(tweet)
    has_video = any(item["type"] in {"video", "animated_gif"} for item in media)
    has_media = bool(media)
    title = f"X 帖子 {status_id}"
    safe_author = escape_markdown_text(normalized(author or "未知"))
    safe_published_at = escape_markdown_text(
        normalized(str(tweet.get("created_at") or "未知"))
    )
    content_path = output / "content.md"
    atomic_text(
        content_path,
        "\n".join(
            [
                f"# {title}",
                "",
                f"- 作者：{safe_author}",
                f"- 发布时间：{safe_published_at}",
                f"- 原文：{canonical_url}",
                "",
                "## 正文",
                "",
                escape_markdown_text(text) if text else "（正文为空）",
            ]
        ),
    )
    limitations: list[str] = []
    if has_video:
        limitations.append("X video media was not downloaded or transcribed.")
    elif has_media:
        limitations.append("X post media was not downloaded by this text route.")
    if not text:
        limitations.append("The public post contained no readable text.")
    content_status = "full_text" if text else "metadata_only"
    receipt = {
        "source_url": source_url,
        "final_url": canonical_url,
        "captured_at": now(),
        "status": "partial" if limitations else "complete",
        "content_status": content_status,
        "acquisition_method": "x_syndication",
        "platform": "x",
        "content_type": "video" if has_video else "article",
        "x_content_kind": "post",
        "title": title,
        "author": author,
        "published_at": str(tweet.get("created_at") or ""),
        "status_id": status_id,
        "content_path": str(content_path),
        "character_count": len(text),
        "structured_content": False,
        "media": media,
        "images": [],
        "images_incomplete": False,
        "images_incomplete_reason": "",
        "limitations": limitations,
    }
    atomic_json(output / "receipt.json", receipt)
    return receipt


def capture(args: argparse.Namespace) -> tuple[dict, int]:
    status_id, canonical_url = parse_status_url(args.url)
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    tweet = fetch_x_status(status_id)
    hint = x_article_reference(tweet)
    if hint is not None:
        receipt = article_capture(
            output, canonical_url, canonical_url, status_id, tweet, hint
        )
    else:
        receipt = post_capture(
            output, canonical_url, canonical_url, status_id, tweet
        )
    return receipt, 0 if receipt["status"] == "complete" else 3


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("url")
    value.add_argument("--output-dir", required=True)
    return value


def main() -> int:
    try:
        receipt, code = capture(parser().parse_args())
    except (OSError, ValueError, UnicodeError, HTTPError, URLError) as exc:
        print(
            json.dumps(
                {"status": "unavailable", "error": str(exc)}, ensure_ascii=False
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
