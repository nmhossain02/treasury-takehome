from __future__ import annotations

import re
import unicodedata

from .models import IdentificationClue, NormalizedSpan


CLASS_WORDS = ("bourbon", "whisky", "whiskey", "gin", "vodka", "rum", "brandy", "tequila")
COUNTRIES = (
    "united kingdom", "canada", "mexico", "france", "italy", "ireland",
    "scotland", "japan", "cayman islands",
)


def normalize(value: str) -> str:
    """Normalize OCR and metadata text for case-insensitive comparison."""

    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _with_reconstructed_lines(
    spans: tuple[NormalizedSpan, ...],
) -> tuple[NormalizedSpan, ...]:
    """Add line spans without changing the provider-neutral OCR contract."""
    groups: dict[tuple[str, int, int], list[NormalizedSpan]] = {}
    for span in spans:
        groups.setdefault((span.image_id, span.block_order, span.line_order), []).append(span)

    lines: list[NormalizedSpan] = []
    for (image_id, block_order, line_order), words in groups.items():
        if len(words) < 2:
            continue
        ordered = sorted(words, key=lambda item: (item.word_order, item.bbox[0]))
        left = min(item.bbox[0] for item in ordered)
        top = min(item.bbox[1] for item in ordered)
        right = max(item.bbox[0] + item.bbox[2] for item in ordered)
        bottom = max(item.bbox[1] + item.bbox[3] for item in ordered)
        lines.append(
            NormalizedSpan(
                text=" ".join(item.text for item in ordered),
                confidence=sum(item.confidence for item in ordered) / len(ordered),
                image_id=image_id,
                bbox=(left, top, right - left, bottom - top),
                block_order=block_order,
                line_order=line_order,
            )
        )
    return (*spans, *lines)


def extract_clues(spans: tuple[NormalizedSpan, ...]) -> list[IdentificationClue]:
    """Derive a bounded set of COLA search clues from provider-neutral OCR spans."""

    clues: list[IdentificationClue] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, span: NormalizedSpan, confidence: float | None = None) -> None:
        value = value.strip()
        key = (kind, normalize(value))
        if not key[1] or key in seen:
            return
        seen.add(key)
        clues.append(IdentificationClue(kind, value, confidence or span.confidence, span.evidence_ref))

    for span in _with_reconstructed_lines(spans):
        text = span.text.strip()
        normalized = normalize(text)
        is_ocr_word = span.word_order > 0
        if not normalized:
            continue
        identifier = re.search(r"\bmock[\s_-]*ttb[\s_-]*(\d+)\b", normalized)
        if identifier:
            add("application_id", f"mock_ttb_{identifier.group(1)}", span)
        for match in re.finditer(r"\b(\d{1,2}(?:\.\d+)?)\s*(?:%|percent)(?:\s*(?:alc(?:ohol)?(?:\s*by\s*volume)?|abv))?", text, re.I):
            add("abv", f"{float(match.group(1)):g}", span)
        for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(ml|milliliters?|l|liters?)\b", text, re.I):
            amount = float(match.group(1))
            if match.group(2).lower().startswith("l"):
                amount *= 1000
            add("net_contents_ml", f"{amount:g}", span)
        if any(word in normalized.split() for word in CLASS_WORDS):
            add("class_type", text, span)
        elif (
            not is_ocr_word
            and 2 <= len(normalized) <= 120
            and not any(character.isdigit() for character in normalized)
            and "government warning" not in normalized
        ):
            # A short non-regulatory display line is a brand/name candidate. Search ranking,
            # not this heuristic, decides which application field it represents.
            add("brand_name", text, span, span.confidence * 0.9)
        for country in COUNTRIES:
            if country in normalized:
                add("country_of_origin", country, span)
        # A line-level text clue allows the mock index to recognize brands and names without
        # teaching this layer the contents of the fixture database.
        if not is_ocr_word and 2 <= len(normalized) <= 120:
            add("text", text, span)

    # The mock search contract is intentionally bounded. Repeated or text-heavy
    # photos must not turn OCR output into an unbounded internal request.
    limits = {
        "application_id": 5,
        "abv": 10,
        "net_contents_ml": 10,
        "class_type": 15,
        "country_of_origin": 10,
        "brand_name": 25,
        "text": 25,
    }
    selected: list[IdentificationClue] = []
    for clue_type, limit in limits.items():
        candidates = sorted(
            (clue for clue in clues if clue.type == clue_type),
            key=lambda clue: clue.confidence,
            reverse=True,
        )
        selected.extend(candidates[:limit])
    return selected
