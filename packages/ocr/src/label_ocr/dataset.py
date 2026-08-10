from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AnnotationSpan:
    text: str
    bbox: tuple[float, float, float, float]
    field_name: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> AnnotationSpan:
        bbox = tuple(float(item) for item in value["bbox"])
        if len(bbox) != 4 or any(item < 0 or item > 1 for item in bbox):
            raise ValueError("annotation bbox must have four normalized values")
        if bbox[0] + bbox[2] > 1.000001 or bbox[1] + bbox[3] > 1.000001:
            raise ValueError("annotation bbox must fit within the image")
        return cls(str(value["text"]), bbox, value.get("field_name"))


@dataclass(frozen=True, slots=True)
class DatasetItem:
    item_id: str
    image_path: str
    media_type: str
    expected_text: str
    annotations: tuple[AnnotationSpan, ...] = ()
    fields: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> DatasetItem:
        required = ("item_id", "image_path", "media_type", "expected_text")
        if any(key not in value for key in required):
            raise ValueError("dataset item is missing a required key")
        return cls(
            item_id=str(value["item_id"]),
            image_path=str(value["image_path"]),
            media_type=str(value["media_type"]),
            expected_text=str(value["expected_text"]),
            annotations=tuple(
                AnnotationSpan.from_dict(item) for item in value.get("annotations", ())
            ),
            fields={
                str(key): str(item) for key, item in value.get("fields", {}).items()
            },
        )


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    schema_version: int
    dataset_name: str
    items: tuple[DatasetItem, ...]

    @classmethod
    def load(cls, path: Path) -> DatasetManifest:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1:
            raise ValueError("unsupported manifest schema_version")
        items = tuple(DatasetItem.from_dict(item) for item in value.get("items", ()))
        if not items:
            raise ValueError("manifest must contain at least one item")
        ids = [item.item_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("manifest item_id values must be unique")
        return cls(1, str(value.get("dataset_name", path.stem)), items)
