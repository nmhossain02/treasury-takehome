from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Protocol


def normalize_text(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def character_error_rate(expected: str, actual: str) -> float:
    expected_normalized = normalize_text(expected)
    actual_normalized = normalize_text(actual)
    return _distance(list(expected_normalized), list(actual_normalized)) / max(
        1, len(expected_normalized)
    )


def word_error_rate(expected: str, actual: str) -> float:
    expected_words = normalize_text(expected).split()
    actual_words = normalize_text(actual).split()
    return _distance(expected_words, actual_words) / max(1, len(expected_words))


class FieldRecallHook(Protocol):
    def score(
        self, expected_fields: Mapping[str, str], actual_text: str
    ) -> Mapping[str, bool]: ...


class ExactNormalizedFieldRecall:
    def score(
        self, expected_fields: Mapping[str, str], actual_text: str
    ) -> Mapping[str, bool]:
        haystack = normalize_text(actual_text)
        return {
            field_name: normalize_text(expected) in haystack
            for field_name, expected in expected_fields.items()
        }


def _distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_value in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_value != right_value),
                )
            )
        previous = current
    return previous[-1]
