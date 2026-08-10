import hashlib
import time
import unittest

from label_ocr import (
    FixtureEntry,
    FixtureOcrProvider,
    OcrImage,
    OcrProvider,
    OcrRequest,
    OcrStatus,
    TextSpan,
)


class ProviderConformanceTests(unittest.IsolatedAsyncioTestCase):
    """Reusable behavioral expectations for every OCR provider adapter."""

    async def test_fixture_satisfies_protocol_and_contract(self):
        content = b"conformance"
        fixture = FixtureEntry(
            (TextSpan("80 Proof", 0.88, "template", (0.1, 0.1, 0.4, 0.1), 1, 1, 1),)
        )
        provider = FixtureOcrProvider({hashlib.sha256(content).hexdigest(): fixture})
        self.assertIsInstance(provider, OcrProvider)
        outcome = await provider.recognize(
            OcrRequest((OcrImage("one", content, "image/jpeg"),), time.monotonic() + 1)
        )
        self.assertEqual(outcome.status, OcrStatus.SUCCESS)
        self.assertEqual(outcome.provider, provider.name)
        self.assertEqual(outcome.version, provider.version)
        self.assertGreaterEqual(outcome.timings["total_ms"], 0)
        self.assertTrue(all(span.image_id == "one" for span in outcome.spans))


if __name__ == "__main__":
    unittest.main()
