from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(_json_ready(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_ready(data: Any) -> Any:
    if hasattr(data, "to_dict"):
        return data.to_dict()
    if is_dataclass(data):
        return asdict(data)
    return data

