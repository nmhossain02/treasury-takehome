from label_verifier.domain.identification import extract_clues
from label_verifier.domain.models import NormalizedSpan


def test_extracts_structured_clues_without_database_knowledge() -> None:
    spans = (
        NormalizedSpan("North Star", .95, "img_1", (0, 0, 1, .1)),
        NormalizedSpan("Straight Bourbon Whisky", .94, "img_1", (0, .1, 1, .1), line_order=1),
        NormalizedSpan("40% ALC/VOL", .98, "img_1", (0, .2, 1, .1), line_order=2),
        NormalizedSpan("0.75 L", .98, "img_1", (0, .3, 1, .1), line_order=3),
    )
    clues = extract_clues(spans)
    values = {(clue.type, clue.value) for clue in clues}
    assert ("brand_name", "North Star") in values
    assert ("abv", "40") in values
    assert ("net_contents_ml", "750") in values


def test_repeated_spans_do_not_duplicate_search_clues() -> None:
    span = NormalizedSpan("750 mL", .9, "img_1", (0, 0, 1, 1))
    clues = extract_clues((span, span))
    assert len([clue for clue in clues if clue.type == "net_contents_ml"]) == 1


def test_reconstructs_multiword_clues_from_tesseract_word_spans() -> None:
    spans = (
        NormalizedSpan("Seven", .96, "front", (0, 0, .2, .1), word_order=1),
        NormalizedSpan("Fathoms", .94, "front", (.22, 0, .3, .1), word_order=2),
        NormalizedSpan("Cayman", .93, "back", (0, .1, .2, .1), line_order=1, word_order=1),
        NormalizedSpan("Islands", .92, "back", (.22, .1, .2, .1), line_order=1, word_order=2),
    )

    values = {(clue.type, clue.value) for clue in extract_clues(spans)}

    assert ("brand_name", "Seven Fathoms") in values
    assert ("country_of_origin", "cayman islands") in values
    assert ("brand_name", "Seven") not in values
    assert ("text", "Fathoms") not in values


def test_bounds_clues_from_text_heavy_images() -> None:
    spans = tuple(
        NormalizedSpan(
            f"Narrative label line {index}", .9, "back", (0, index / 200, 1, .01),
            line_order=index,
        )
        for index in range(150)
    )

    clues = extract_clues(spans)

    assert len(clues) <= 100
    assert len([clue for clue in clues if clue.type == "text"]) <= 25
