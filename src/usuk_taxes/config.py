"""Project paths and settings.

The project root is located by walking up from the current directory until a
corpus/manifest.yaml is found, so `usuk` works from any subdirectory. Override
with the USUK_ROOT environment variable.
"""

import os
from pathlib import Path


def find_root() -> Path:
    if "USUK_ROOT" in os.environ:
        return Path(os.environ["USUK_ROOT"]).resolve()
    d = Path.cwd().resolve()
    for candidate in [d, *d.parents]:
        if (candidate / "corpus" / "manifest.yaml").exists():
            return candidate
    raise SystemExit(
        "Could not find corpus/manifest.yaml in this directory or any parent. "
        "Run from the project directory or set USUK_ROOT."
    )


ROOT = find_root()

# Load ROOT/.env (KEY=value lines) for anything not already in the environment,
# so ANTHROPIC_API_KEY can live in a gitignored file.
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
MANIFEST_PATH = ROOT / "corpus" / "manifest.yaml"
RAW_DIR = ROOT / "corpus" / "raw"
TEXT_DIR = ROOT / "corpus" / "text"
DATA_DIR = ROOT / "data"
CHUNKS_PATH = DATA_DIR / "chunks.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"

# Personal files (real profile, working workbooks) live outside the repo, in
# the directory named by USUK_PRIVATE_DIR. Without it, the tracked example
# profile is used and workbooks go to spreadsheets/ (gitignored).
PRIVATE_DIR = (
    Path(os.environ["USUK_PRIVATE_DIR"]).expanduser().resolve()
    if os.environ.get("USUK_PRIVATE_DIR")
    else None
)
EXAMPLE_PROFILE_PATH = ROOT / "profile.example.yaml"
if PRIVATE_DIR and (PRIVATE_DIR / "profile.yaml").exists():
    PROFILE_PATH = PRIVATE_DIR / "profile.yaml"
else:
    PROFILE_PATH = EXAMPLE_PROFILE_PATH

MODEL = os.environ.get("USUK_MODEL", "claude-opus-4-8")

# Chunking: target size in characters (~350-400 tokens) with overlap.
CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200

# Retrieval: candidates pulled from each retriever, and final passages sent to
# the model after hybrid fusion.
RETRIEVE_K = 40
FINAL_K = 12
