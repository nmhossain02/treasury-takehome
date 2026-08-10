import unittest

from label_ocr.metrics import (
    ExactNormalizedFieldRecall,
    character_error_rate,
    word_error_rate,
)


class MetricsTests(unittest.TestCase):
    def test_exact_text_has_zero_error(self):
        self.assertEqual(character_error_rate("Bottled in Bond", "Bottled in Bond"), 0)
        self.assertEqual(word_error_rate("Bottled in Bond", "Bottled in Bond"), 0)

    def test_known_word_error(self):
        self.assertAlmostEqual(
            word_error_rate("straight bourbon whiskey", "straight whiskey"), 1 / 3
        )

    def test_field_hook_is_case_and_punctuation_insensitive(self):
        result = ExactNormalizedFieldRecall().score(
            {"abv": "45% Alc./Vol.", "volume": "750 mL"},
            "45 Alc Vol — 750 ml",
        )
        self.assertEqual(result, {"abv": True, "volume": True})


if __name__ == "__main__":
    unittest.main()
