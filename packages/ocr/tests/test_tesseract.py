import asyncio
import shutil
import time
import unittest
from unittest.mock import AsyncMock, patch

from label_ocr import (
    OcrImage,
    OcrRequest,
    OcrStatus,
    TesseractConfig,
    TesseractOcrProvider,
)
from label_ocr.preprocess import CoordinateMap, PreprocessedImage
from label_ocr.tesseract import parse_tesseract_tsv

TSV = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
1\t1\t0\t0\t0\t0\t0\t0\t200\t100\t-1\t
5\t1\t1\t1\t2\t3\t20\t10\t100\t20\t92.5\tBourbon
5\t1\t1\t1\t2\t4\t20\t40\t100\t20\t-1\tIgnored
"""


class TsvTests(unittest.TestCase):
    def test_parses_words_and_normalizes_boxes(self):
        result = parse_tesseract_tsv(TSV, "photo", CoordinateMap(400, 200, 200, 100))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "Bourbon")
        self.assertAlmostEqual(result[0].confidence, 0.925)
        self.assertEqual(result[0].bbox, (0.1, 0.1, 0.5, 0.2))

    def test_rejects_invalid_header(self):
        with self.assertRaises(RuntimeError):
            parse_tesseract_tsv("text\nhello\n", "photo", CoordinateMap(1, 1, 1, 1))


class TesseractDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_image_timeout_and_one_success_is_partial(self):
        provider = TesseractOcrProvider(TesseractConfig(per_image_timeout_seconds=0.01))
        provider._invoke = AsyncMock(
            side_effect=(
                asyncio.TimeoutError(),
                TSV,
            )
        )
        processed = PreprocessedImage(
            b"processed",
            "image/png",
            CoordinateMap(200, 100, 200, 100),
        )
        with patch("label_ocr.tesseract.preprocess_image", return_value=processed):
            result = await provider.recognize(
                OcrRequest(
                    (
                        OcrImage("slow", b"slow", "image/png"),
                        OcrImage("good", b"good", "image/png"),
                    ),
                    time.monotonic() + 1,
                )
            )
        self.assertEqual(result.status, OcrStatus.PARTIAL)
        self.assertIn("image_timeout", result.error_codes)
        self.assertEqual(result.spans[0].image_id, "good")


@unittest.skipUnless(shutil.which("tesseract"), "real Tesseract is not installed")
class RealTesseractSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_generated_text(self):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow is not installed")
        import io

        image = Image.new("RGB", (700, 180), "white")
        ImageDraw.Draw(image).text(
            (30, 60), "BOURBON 45% ALC/VOL", fill="black", font_size=36
        )
        output = io.BytesIO()
        image.save(output, "PNG")
        result = await TesseractOcrProvider().recognize(
            OcrRequest(
                (OcrImage("smoke", output.getvalue(), "image/png"),),
                time.monotonic() + 5,
            )
        )
        self.assertIn(result.status, (OcrStatus.SUCCESS, OcrStatus.PARTIAL))
        self.assertTrue(result.spans)


if __name__ == "__main__":
    unittest.main()
