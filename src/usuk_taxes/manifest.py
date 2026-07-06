"""Load and validate the corpus manifest."""

from dataclasses import dataclass

import yaml

from .config import MANIFEST_PATH, RAW_DIR, TEXT_DIR


@dataclass
class Source:
    id: str
    jurisdiction: str
    title: str
    url: str
    type: str  # "pdf" | "html"

    @property
    def raw_path(self):
        ext = "pdf" if self.type == "pdf" else "html"
        return RAW_DIR / f"{self.id}.{ext}"

    @property
    def text_path(self):
        return TEXT_DIR / f"{self.id}.txt"


def load_sources() -> list[Source]:
    with open(MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    sources = [Source(**entry) for entry in data["sources"]]
    ids = [s.id for s in sources]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"Duplicate source ids in manifest: {dupes}")
    return sources
