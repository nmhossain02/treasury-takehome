import io
import unittest

from label_ocr.preprocess import preprocess_image


class PreprocessTests(unittest.TestCase):
    def setUp(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        self.Image = Image

    def test_resizes_and_preserves_normalized_coordinates(self):
        image = self.Image.new("RGB", (400, 200), "white")
        content = io.BytesIO()
        image.save(content, "PNG")
        result = preprocess_image(content.getvalue(), max_dimension=100)
        self.assertEqual(
            (
                result.coordinate_map.processed_width,
                result.coordinate_map.processed_height,
            ),
            (100, 50),
        )
        self.assertEqual(
            result.coordinate_map.to_source_normalized((10, 5, 20, 10)),
            (0.1, 0.1, 0.2, 0.2),
        )

    def test_invalid_bytes_are_rejected(self):
        with self.assertRaises(ValueError):
            preprocess_image(b"not an image")


if __name__ == "__main__":
    unittest.main()
