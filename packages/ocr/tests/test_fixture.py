import hashlib
import time
import unittest

from label_ocr import (
    FixtureEntry,
    FixtureOcrProvider,
    OcrImage,
    OcrRequest,
    OcrStatus,
    TextSpan,
)


class FixtureTests(unittest.IsolatedAsyncioTestCase):
    async def test_digest_hit_rewrites_image_id(self):
        content = b"known"
        span = TextSpan("Bourbon", 0.95, "template", (0, 0, 1, 1), 0, 0, 0)
        provider = FixtureOcrProvider(
            {hashlib.sha256(content).hexdigest(): FixtureEntry((span,))}
        )
        result = await provider.recognize(
            OcrRequest(
                (OcrImage("photo-1", content, "image/png"),), time.monotonic() + 1
            )
        )
        self.assertEqual(result.status, OcrStatus.SUCCESS)
        self.assertEqual(result.spans[0].image_id, "photo-1")

    async def test_unknown_digest_fails(self):
        provider = FixtureOcrProvider({})
        result = await provider.recognize(
            OcrRequest(
                (OcrImage("photo", b"unknown", "image/png"),), time.monotonic() + 1
            )
        )
        self.assertEqual(result.status, OcrStatus.FAILED)
        self.assertIn("fixture_not_found", result.error_codes)

    async def test_mixed_known_and_unknown_is_partial(self):
        known = b"known"
        span = TextSpan("Gin", 1, "template", (0, 0, 1, 1), 0, 0, 0)
        provider = FixtureOcrProvider(
            {hashlib.sha256(known).hexdigest(): FixtureEntry((span,))}
        )
        result = await provider.recognize(
            OcrRequest(
                (
                    OcrImage("known", known, "image/png"),
                    OcrImage("unknown", b"unknown", "image/png"),
                ),
                time.monotonic() + 1,
            )
        )
        self.assertEqual(result.status, OcrStatus.PARTIAL)
        self.assertEqual(len(result.spans), 1)

    async def test_bounded_delay_observes_deadline(self):
        content = b"slow"
        provider = FixtureOcrProvider(
            {hashlib.sha256(content).hexdigest(): FixtureEntry(delay_seconds=0.1)}
        )
        result = await provider.recognize(
            OcrRequest(
                (OcrImage("slow", content, "image/png"),), time.monotonic() + 0.01
            )
        )
        self.assertEqual(result.status, OcrStatus.FAILED)
        self.assertIn("deadline_exceeded", result.error_codes)


if __name__ == "__main__":
    unittest.main()
