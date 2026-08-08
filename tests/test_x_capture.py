from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from http.client import IncompleteRead
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "cyber-bookhouse"
    / "scripts"
    / "x_capture.py"
)
SPEC = importlib.util.spec_from_file_location("x_capture", SCRIPT)
assert SPEC and SPEC.loader
X = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(X)

STATUS_ID = "1234567890123456789"
ARTICLE_ID = "9876543210987654321"
STATUS_URL = f"https://x.com/example/status/{STATUS_ID}?s=46"
ARTICLE_URL = f"https://x.com/i/article/{ARTICLE_ID}"


def base_tweet() -> dict:
    return {
        "id_str": STATUS_ID,
        "text": "A complete public post.",
        "created_at": "2026-08-08T00:00:00.000Z",
        "lang": "en",
        "user": {"name": "Example", "screen_name": "example"},
    }


def article_tweet() -> dict:
    value = base_tweet()
    value.update(
        {
            "text": "https://t.co/preview",
            "article": {
                "rest_id": ARTICLE_ID,
                "title": "Preview title",
                "preview_text": "Preview only",
            },
            "entities": {
                "urls": [{"expanded_url": f"http://x.com/i/article/{ARTICLE_ID}"}]
            },
        }
    )
    return value


def image(media_id: str, name: str) -> dict:
    return {
        "media_id": media_id,
        "media_info": {
            "original_img_url": f"https://pbs.twimg.com/media/{name}.jpg"
        },
    }


def fake_download_image(url, target_stem, **_kwargs):
    target = target_stem.with_suffix(".jpg")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\xff\xd8\xff" + b"0" * 9)
    return target, {
        "filename": target.name,
        "relative_path": f"assets/{target.name}",
        "bytes": 12,
        "sha256": "0" * 64,
        "content_type": "image/jpeg",
        "source_url": url,
    }


class XCaptureTests(unittest.TestCase):
    def test_status_url_is_strict_and_canonical(self) -> None:
        status_id, canonical = X.parse_status_url(
            f"https://twitter.com/example/status/{STATUS_ID}/photo/1?s=20"
        )
        self.assertEqual(status_id, STATUS_ID)
        self.assertEqual(canonical, f"https://x.com/i/status/{STATUS_ID}")
        rejected = (
            f"http://x.com/example/status/{STATUS_ID}",
            f"https://user@x.com/example/status/{STATUS_ID}",
            f"https://x.com:444/example/status/{STATUS_ID}",
            f"https://example.com/example/status/{STATUS_ID}",
            "https://x.com/home",
        )
        for url in rejected:
            with self.subTest(url=url), self.assertRaises(ValueError):
                X.parse_status_url(url)

    def test_syndication_identity_must_match(self) -> None:
        payload = json.dumps({"id_str": "111", "text": "wrong"}).encode()
        with mock.patch.object(
            X, "fetch_bytes", return_value=(payload, "", {})
        ):
            with self.assertRaisesRegex(ValueError, "identity"):
                X.fetch_x_status(STATUS_ID)

    def test_normal_post_writes_compatible_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            args = type(
                "Args",
                (),
                {"url": STATUS_URL, "output_dir": folder},
            )()
            with mock.patch.object(X, "fetch_x_status", return_value=base_tweet()):
                receipt, code = X.capture(args)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(receipt["content_status"], "full_text")
            self.assertEqual(receipt["x_content_kind"], "post")
            self.assertIn(
                "A complete public post.",
                (Path(folder) / "content.md").read_text(encoding="utf-8"),
            )
            stored = json.loads(
                (Path(folder) / "receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["status_id"], STATUS_ID)

    def test_post_markdown_control_sequences_are_escaped(self) -> None:
        tweet = base_tweet()
        tweet["text"] = "![tracking](https://attacker.example/pixel)\n![[Private Note]]"
        tweet["user"]["name"] = "![[Private Author]]"
        with tempfile.TemporaryDirectory() as folder:
            X.post_capture(
                Path(folder),
                STATUS_URL,
                f"https://x.com/i/status/{STATUS_ID}",
                STATUS_ID,
                tweet,
            )
            content = (Path(folder) / "content.md").read_text(encoding="utf-8")
        self.assertNotIn("![tracking](https://attacker.example/pixel)", content)
        self.assertNotIn("![[Private Note]]", content)
        self.assertNotIn("![[Private Author]]", content)
        self.assertIn(r"\!\[tracking\]", content)
        self.assertIn(r"\!\[\[Private Author\]\]", content)

    def test_video_post_is_partial_without_claiming_media_body(self) -> None:
        tweet = base_tweet()
        tweet["mediaDetails"] = [
            {
                "type": "video",
                "original_info": {"width": 1920, "height": 1080},
                "video_info": {
                    "duration_millis": 12000,
                    "variants": [{"url": "https://video.twimg.com/secret.mp4"}],
                },
            }
        ]
        with tempfile.TemporaryDirectory() as folder:
            receipt = X.post_capture(
                Path(folder),
                STATUS_URL,
                f"https://x.com/i/status/{STATUS_ID}",
                STATUS_ID,
                tweet,
            )
        self.assertEqual(receipt["status"], "partial")
        self.assertEqual(receipt["content_status"], "full_text")
        self.assertEqual(receipt["content_type"], "video")
        self.assertNotIn("secret.mp4", json.dumps(receipt))
        self.assertIn("not downloaded or transcribed", receipt["limitations"][0])

    def test_article_uses_full_draftjs_body_and_inline_image_order(self) -> None:
        article = {
            "rest_id": ARTICLE_ID,
            "title": "Full article title",
            "plain_text": "Preview only",
            "cover_media": image("cover", "cover"),
            "media_entities": [
                image("first", "first"),
                image("second", "second"),
            ],
            "content_state": {
                "blocks": [
                    {"type": "header-one", "text": "First section", "depth": 0},
                    {
                        "type": "unstyled",
                        "text": "This is the verified complete article body.",
                        "depth": 0,
                    },
                    {
                        "type": "atomic",
                        "text": " ",
                        "entityRanges": [{"key": 0, "offset": 0, "length": 1}],
                    },
                    {"type": "blockquote", "text": "Quoted evidence", "depth": 0},
                    {"type": "unordered-list-item", "text": "Point A", "depth": 0},
                    {"type": "ordered-list-item", "text": "Step one", "depth": 0},
                    {"type": "code-block", "text": "print('ok')", "depth": 0},
                    {
                        "type": "atomic",
                        "text": " ",
                        "entityRanges": [{"key": 1, "offset": 0, "length": 1}],
                    },
                ],
                "entityMap": [
                    {
                        "key": "0",
                        "value": {
                            "type": "MEDIA",
                            "data": {"mediaItems": [{"mediaId": "second"}]},
                        },
                    },
                    {
                        "key": "1",
                        "value": {
                            "type": "MEDIA",
                            "data": {"mediaItems": [{"mediaId": "first"}]},
                        },
                    },
                ],
            },
        }
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "fetch_x_article_public", return_value=article
        ), mock.patch.object(
            X, "download_image", side_effect=fake_download_image
        ):
            receipt = X.article_capture(
                Path(folder),
                STATUS_URL,
                f"https://x.com/i/status/{STATUS_ID}",
                STATUS_ID,
                article_tweet(),
                X.x_article_reference(article_tweet()),
            )
            content = (Path(folder) / "content.md").read_text(encoding="utf-8")
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["article_id"], ARTICLE_ID)
        self.assertEqual(len(receipt["images"]), 3)
        self.assertIn("## First section", content)
        self.assertIn("> Quoted evidence", content)
        self.assertIn("- Point A", content)
        self.assertIn("1. Step one", content)
        self.assertIn("```\nprint('ok')\n```", content)
        self.assertLess(content.index("image-03.jpg"), content.index("image-02.jpg"))
        self.assertNotIn("Preview only", content)

    def test_article_markdown_is_escaped_and_code_fence_cannot_break_out(self) -> None:
        article = {
            "rest_id": ARTICLE_ID,
            "title": "![[Private Title]]",
            "plain_text": "A complete public article body.",
            "content_state": {
                "blocks": [
                    {
                        "type": "unstyled",
                        "text": "![tracking](https://attacker.example/pixel)",
                    },
                    {"type": "code-block", "text": "```"},
                    {"type": "code-block", "text": "![[Private Code]]"},
                ],
                "entityMap": {},
            },
        }
        tweet = article_tweet()
        tweet["user"]["name"] = "![[Private Author]]"
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "fetch_x_article_public", return_value=article
        ), mock.patch.object(
            X, "download_x_article_images", return_value=([], {}, {
                "images_incomplete": False,
                "images_incomplete_reason": "",
                "image_bytes_downloaded": 0,
            })
        ):
            X.article_capture(
                Path(folder),
                STATUS_URL,
                f"https://x.com/i/status/{STATUS_ID}",
                STATUS_ID,
                tweet,
                X.x_article_reference(tweet),
            )
            content = (Path(folder) / "content.md").read_text(encoding="utf-8")
        self.assertNotIn("# ![[Private Title]]", content)
        self.assertNotIn("- 作者：![[Private Author]]", content)
        self.assertNotIn("![tracking](https://attacker.example/pixel)", content)
        self.assertIn("````\n```\n![[Private Code]]\n````", content)

    def test_article_identity_mismatch_fails_before_images(self) -> None:
        article = {
            "rest_id": "1111111111111111111",
            "plain_text": "A complete-looking but mismatched article body.",
        }
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "fetch_x_article_public", return_value=article
        ), mock.patch.object(X, "download_x_article_images") as download:
            with self.assertRaisesRegex(ValueError, "identity"):
                X.article_capture(
                    Path(folder),
                    STATUS_URL,
                    f"https://x.com/i/status/{STATUS_ID}",
                    STATUS_ID,
                    article_tweet(),
                    X.x_article_reference(article_tweet()),
                )
            download.assert_not_called()
            self.assertFalse((Path(folder) / "content.md").exists())

    def test_preview_shortlink_and_login_prompt_are_rejected(self) -> None:
        cases = (
            ("Preview only", "Preview only"),
            ("https://t.co/abc123", "https://t.co/abc123"),
            ("Log in to X", "Log in to X"),
            (
                "Preview only",
                "Preview only — Log in to X to read the full article.",
            ),
            (
                "Different preview",
                "https://t.co/abc123 — Sign up for X to continue.",
            ),
        )
        for preview, body in cases:
            with self.subTest(body=body):
                tweet = article_tweet()
                tweet["article"]["preview_text"] = preview
                article = {"plain_text": body, "content_state": {}}
                with self.assertRaisesRegex(
                    ValueError, "X_ARTICLE_BODY_UNAVAILABLE"
                ):
                    X.validate_article_body(
                        article, X.x_article_reference(tweet), tweet
                    )

    def test_public_guest_tokens_are_not_returned_or_leaked(self) -> None:
        bearer = "A" * 24 + "B" * 64 + "%2F%3D"
        guest = "guest-secret-123"
        graph = {
            "data": {
                "tweetResult": {
                    "result": {
                        "rest_id": STATUS_ID,
                        "article": {
                            "article_results": {
                                "result": {
                                    "rest_id": ARTICLE_ID,
                                    "title": "Title",
                                    "plain_text": "A verified full article body.",
                                }
                            }
                        },
                    }
                }
            }
        }
        network = [
            (
                json.dumps({"guest_token": guest}).encode(),
                "https://api.x.com/",
                {},
            ),
            (json.dumps(graph).encode(), "https://x.com/", {}),
        ]
        with mock.patch.object(
            X, "x_public_web_credentials", return_value=(bearer, "QueryId_123456")
        ), mock.patch.object(X, "x_request_bytes", side_effect=network) as request:
            result = X.fetch_x_article_public(STATUS_ID, ARTICLE_URL)
        serialized = json.dumps(result)
        self.assertNotIn(bearer, serialized)
        self.assertNotIn(guest, serialized)
        self.assertNotIn(bearer, request.call_args_list[1].args[0])
        self.assertNotIn(guest, request.call_args_list[1].args[0])

    def test_public_guest_failure_is_sanitized(self) -> None:
        secret = "A" * 96
        with mock.patch.object(
            X, "x_public_web_credentials", return_value=(secret, "QueryId_123456")
        ), mock.patch.object(
            X, "x_request_bytes", side_effect=ValueError(f"failed {secret}")
        ):
            with self.assertRaises(ValueError) as raised:
                X.fetch_x_article_public(STATUS_ID, ARTICLE_URL)
        self.assertIn("X_ARTICLE_BODY_UNAVAILABLE", str(raised.exception))
        self.assertNotIn(secret, str(raised.exception))

    def test_x_json_request_retries_a_truncated_success_response(self) -> None:
        responses = [
            (b'{"data":', "https://x.com/", {}),
            (b'{"data": {"ok": true}}', "https://x.com/", {}),
        ]
        with mock.patch.object(
            X, "x_request_bytes", side_effect=responses
        ) as request, mock.patch.object(X.time, "sleep") as sleep:
            payload = X.x_request_json("https://x.com/i/api/graphql/example")
        self.assertEqual(payload, {"data": {"ok": True}})
        self.assertEqual(request.call_count, 2)
        self.assertTrue(
            all(call.kwargs["attempts"] == 1 for call in request.call_args_list)
        )
        sleep.assert_called_once_with(1)

    def test_x_json_request_has_one_total_three_attempt_budget(self) -> None:
        with mock.patch.object(
            X,
            "x_request_bytes",
            return_value=(b"", "https://x.com/", {}),
        ) as request, mock.patch.object(X.time, "sleep") as sleep:
            with self.assertRaisesRegex(ValueError, "remained incomplete"):
                X.x_request_json("https://x.com/i/api/graphql/example")
        self.assertEqual(request.call_count, 3)
        self.assertTrue(
            all(call.kwargs["attempts"] == 1 for call in request.call_args_list)
        )
        self.assertEqual(sleep.call_args_list, [mock.call(1), mock.call(3)])

    def test_graphql_status_identity_is_required(self) -> None:
        article = {
            "article": {
                "article_results": {
                    "result": {"rest_id": ARTICLE_ID, "plain_text": "body"}
                }
            }
        }
        for result in (article, {**article, "rest_id": "111"}):
            payload = {"data": {"tweetResult": {"result": result}}}
            with self.subTest(result=result), self.assertRaisesRegex(
                ValueError, "identity"
            ):
                X.x_article_result_from_graphql(payload, STATUS_ID)

    def test_article_reference_ids_must_match(self) -> None:
        tweet = article_tweet()
        tweet["entities"]["urls"][0]["expanded_url"] = (
            "https://x.com/i/article/1111111111111111111"
        )
        with self.assertRaisesRegex(ValueError, "reference IDs"):
            X.x_article_reference(tweet)

    def test_main_bundle_and_credentials_are_strict(self) -> None:
        expected = (
            "https://abs.twimg.com/responsive-web/client-web/main.27ea3f4a.js"
        )
        pages = (
            f'<script src="{expected}"></script>',
            f'<link rel="preload" as="script" href="{expected}">',
        )
        for page in pages:
            with self.subTest(page=page):
                self.assertEqual(
                    X.x_main_script_url(page, "https://x.com/home"), expected
                )
        with self.assertRaises(ValueError):
            X.x_main_script_url(
                '<script src="https://example.com/main.bad.js"></script>',
                "https://x.com/home",
            )
        bearer = "A" * 96
        bundle = (
            f'const token="{bearer}";'
            'const route={queryId:"QueryId_123456",'
            'operationName:"TweetResultByRestId"};'
        )
        self.assertEqual(
            X.x_bundle_credentials(bundle), (bearer, "QueryId_123456")
        )

    def test_image_urls_and_redirects_stay_on_pbs_https(self) -> None:
        url = X.x_media_url(image("one", "one"))
        self.assertEqual(url, "https://pbs.twimg.com/media/one.jpg?name=orig")
        rejected = (
            "http://pbs.twimg.com/media/one.jpg",
            "https://user@pbs.twimg.com/media/one.jpg",
            "https://pbs.twimg.com:444/media/one.jpg",
            "https://example.com/media/one.jpg",
        )
        for candidate in rejected:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                X.validate_x_media_url(candidate)
        handler = X.AllowedHostsRedirect({"pbs.twimg.com"})
        with self.assertRaisesRegex(ValueError, "allowed HTTPS media hosts"):
            handler.redirect_request(
                None, None, 302, "Found", {}, "https://example.com/stolen.jpg"
            )
        with self.assertRaisesRegex(ValueError, "official X HTTPS hosts"):
            X.SafeRedirect().redirect_request(
                None, None, 302, "Found", {}, "https://example.com/stolen"
            )

    def test_image_signature_rejects_html_svg_and_unknown(self) -> None:
        self.assertEqual(X.sniff_image_type(b"\xff\xd8\xffabc")[0], ".jpg")
        self.assertEqual(
            X.sniff_image_type(b"\x89PNG\r\n\x1a\nabc")[0], ".png"
        )
        self.assertEqual(X.sniff_image_type(b"GIF89aabc")[0], ".gif")
        self.assertEqual(
            X.sniff_image_type(b"RIFF0000WEBPabc")[0], ".webp"
        )
        for payload in (b"<html>login</html>", b"<svg></svg>", b"unknown"):
            with self.subTest(payload=payload), self.assertRaises(
                X.UnsupportedImageType
            ):
                X.sniff_image_type(payload)

    def test_total_image_budget_keeps_downloaded_images_and_marks_partial(self) -> None:
        article = {
            "media_entities": [image("one", "one"), image("two", "two")]
        }
        calls: list[int] = []

        def limited(url, target_stem, **kwargs):
            calls.append(kwargs["limit"])
            if len(calls) == 2:
                raise X.DownloadSizeLimitExceeded("aggregate")
            return fake_download_image(url, target_stem, **kwargs)

        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "download_image", side_effect=limited
        ), mock.patch.object(X, "MAX_IMAGE_TOTAL_BYTES", 20):
            records, _, state = X.download_x_article_images(
                Path(folder), STATUS_URL, article, {}
            )
        self.assertEqual(calls, [20, 8])
        self.assertEqual(len(records), 1)
        self.assertTrue(state["images_incomplete"])
        self.assertEqual(
            state["images_incomplete_reason"], "total_byte_budget_exhausted"
        )

    def test_article_body_survives_partial_images(self) -> None:
        article = {
            "rest_id": ARTICLE_ID,
            "title": "Full title",
            "plain_text": "A verified complete article body.",
        }
        image_state = {
            "images_incomplete": True,
            "images_incomplete_reason": "image_download_timeout",
            "image_bytes_downloaded": 0,
        }
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "fetch_x_article_public", return_value=article
        ), mock.patch.object(
            X, "download_x_article_images", return_value=([], {}, image_state)
        ):
            receipt = X.article_capture(
                Path(folder),
                STATUS_URL,
                f"https://x.com/i/status/{STATUS_ID}",
                STATUS_ID,
                article_tweet(),
                X.x_article_reference(article_tweet()),
            )
            content = (Path(folder) / "content.md").read_text(encoding="utf-8")
        self.assertEqual(receipt["status"], "partial")
        self.assertEqual(receipt["content_status"], "full_text")
        self.assertIn("A verified complete article body.", content)
        self.assertIn("images_incomplete=true", content)

    def test_missing_media_url_and_unresolved_inline_image_are_partial(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            records, _, state = X.download_x_article_images(
                Path(folder),
                STATUS_URL,
                {"media_entities": [{"media_id": "lost"}]},
                {},
            )
        self.assertEqual(records, [])
        self.assertEqual(state["images_incomplete_reason"], "image_url_missing")

        article = {
            "rest_id": ARTICLE_ID,
            "title": "Full title",
            "plain_text": "A verified complete article body.",
            "content_state": {
                "blocks": [
                    {
                        "type": "unstyled",
                        "text": "A verified complete article body.",
                    },
                    {
                        "type": "atomic",
                        "text": " ",
                        "entityRanges": [{"key": 0, "offset": 0, "length": 1}],
                    },
                ],
                "entityMap": {
                    "0": {
                        "type": "MEDIA",
                        "data": {"mediaItems": [{"mediaId": "lost"}]},
                    }
                },
            },
        }
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "fetch_x_article_public", return_value=article
        ):
            receipt = X.article_capture(
                Path(folder),
                STATUS_URL,
                f"https://x.com/i/status/{STATUS_ID}",
                STATUS_ID,
                article_tweet(),
                X.x_article_reference(article_tweet()),
            )
        self.assertEqual(receipt["status"], "partial")
        self.assertEqual(
            receipt["images_incomplete_reason"], "inline_image_unresolved"
        )

    def test_images_are_deduplicated_and_capped_at_thirty(self) -> None:
        media = [image(str(index), str(index)) for index in range(31)]
        article = {"cover_media": media[0], "media_entities": media}
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "download_image", side_effect=fake_download_image
        ) as download:
            records, aliases, state = X.download_x_article_images(
                Path(folder), STATUS_URL, article, {}
            )
        self.assertEqual(len(records), 30)
        self.assertEqual(download.call_count, 30)
        self.assertEqual(aliases["0"], "assets/image-01.jpg")
        self.assertNotIn("30", aliases)
        self.assertEqual(state["images_incomplete_reason"], "image_count_limit_reached")

    def test_bounded_read_keeps_incomplete_proxy_payload(self) -> None:
        response = mock.Mock()
        response.headers = {}
        response.read.side_effect = IncompleteRead(b"partial", 3)
        self.assertEqual(X.bounded_read(response, 100), b"partial")

    def test_image_download_resumes_a_short_proxy_response(self) -> None:
        payload = b"\xff\xd8\xff" + b"abcdefg" + b"\xff\xd9"

        class Response:
            def __init__(self, data, headers, status):
                self.data = data
                self.headers = headers
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size):
                data, self.data = self.data, b""
                return data

        responses = [
            Response(
                payload[:6],
                {"Content-Length": str(len(payload)), "Content-Type": "image/jpeg"},
                200,
            ),
            Response(
                payload[6:],
                {
                    "Content-Length": str(len(payload) - 6),
                    "Content-Range": f"bytes 6-{len(payload) - 1}/{len(payload)}",
                    "Content-Type": "image/jpeg",
                },
                206,
            ),
        ]
        ranges: list[str | None] = []

        class Opener:
            def open(self, request, timeout):
                self.assert_timeout = timeout
                ranges.append(request.get_header("Range"))
                return responses.pop(0)

        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            X, "validate_x_media_url", side_effect=lambda value: value
        ), mock.patch.object(X, "build_opener", return_value=Opener()):
            target, record = X.download_image(
                "https://pbs.twimg.com/media/example.jpg",
                Path(folder) / "image-01",
                referer=STATUS_URL,
                limit=100,
                timeout=10,
                deadline=X.time.monotonic() + 10,
            )
            self.assertEqual(target.read_bytes(), payload)
        self.assertEqual(ranges, [None, "bytes=6-"])
        self.assertEqual(record["bytes"], len(payload))

    def test_cli_rejects_non_https_without_writing_content(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            run = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    f"http://x.com/example/status/{STATUS_ID}",
                    "--output-dir",
                    folder,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 1)
            self.assertIn('"status": "unavailable"', run.stderr)
            self.assertFalse((Path(folder) / "content.md").exists())


if __name__ == "__main__":
    unittest.main()
