"""Download corpus sources and extract plain text.

Raw downloads are cached in corpus/raw/ and extracted text in corpus/text/,
so re-chunking or re-indexing never needs the network.
"""

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .config import RAW_DIR, TEXT_DIR
from .manifest import Source

HEADERS = {
    # Some government sites reject requests without a browser-ish user agent.
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) usuk-taxes/0.1 (personal tax research tool)"
}


def fetch(source: Source, force: bool = False) -> bool:
    """Download a source to corpus/raw/. Returns True if downloaded."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if source.raw_path.exists() and not force:
        return False
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=60) as client:
        resp = client.get(source.url)
        resp.raise_for_status()
        source.raw_path.write_bytes(resp.content)
    return True


def extract_text(source: Source, force: bool = False) -> str:
    """Extract plain text from a downloaded source, cached in corpus/text/."""
    if source.text_path.exists() and not force:
        return source.text_path.read_text()
    if not source.raw_path.exists():
        raise FileNotFoundError(f"{source.id}: not downloaded yet (run `usuk fetch`)")

    if source.type == "pdf":
        reader = PdfReader(source.raw_path)
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[page {i}]\n{text}")
        text = "\n\n".join(pages)
    else:
        soup = BeautifulSoup(source.raw_path.read_bytes(), "lxml")
        # gov.uk keeps article content in <main>; fall back to whole body.
        main = soup.find("main") or soup.body or soup
        for tag in main.find_all(["nav", "script", "style", "footer", "header", "aside"]):
            tag.decompose()
        text = main.get_text("\n", strip=True)

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    source.text_path.write_text(text)
    return text
