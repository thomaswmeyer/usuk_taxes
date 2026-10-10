"""Answer tax questions with Claude, grounded in retrieved corpus passages.

Retrieved chunks are passed as document content blocks with the API's native
citations feature enabled, so every claim in the answer is tied to a quoted
passage from an authoritative source.
"""

import os

import yaml
from anthropic import Anthropic

from .config import FINAL_K, MODEL, PROFILE_PATH
from .index import search

NOTE = "Research tool only, not tax advice. Verify against the cited sources or a qualified professional before relying on it."

SYSTEM_PROMPT = """\
You are a careful US/UK cross-border tax research tool helping a US
citizen resident in the UK prepare their own US federal return (tax year 2025)
and UK Self Assessment (tax year 2025-26).

Household profile:
{profile}

Rules:
- Ground every substantive claim in the provided documents and cite them. If
  the documents don't cover the question, say so plainly rather than guessing.
- Always state which tax year and jurisdiction a rule applies to. US and UK
  tax years differ (calendar year vs 6 April-5 April); flag apportionment
  issues where they interact.
- Watch for treaty interactions (saving clause, re-sourcing, tie-breakers) and
  say when the US-UK treaty modifies the default rule.
- Where figures depend on facts not in the profile, state the assumption you
  are making.
- You provide research, not tax advice. Never present an answer as advice or
  as a recommendation the reader can rely on without checking the sources.
- End answers that involve judgment calls or high stakes (equity compensation
  sourcing, treaty positions, PFICs) with a short note on what to verify or
  when a cross-border professional is warranted.
"""


def _profile_text() -> str:
    if PROFILE_PATH.exists():
        return yaml.safe_dump(yaml.safe_load(PROFILE_PATH.read_text()), sort_keys=False)
    return "(no profile found)"


def ask(question: str, k: int = FINAL_K, show_passages: bool = False) -> None:
    passages = search(question, k=k)

    if show_passages:
        for p in passages:
            print(f"--- {p['id']} ({p['title']})")
            print(p["text"][:300].replace("\n", " ") + " ...\n")

    content = []
    for p in passages:
        content.append(
            {
                "type": "document",
                "source": {"type": "text", "media_type": "text/plain", "data": p["text"]},
                "title": f"{p['title']} [{p['id']}]",
                "citations": {"enabled": True},
            }
        )
    content.append({"type": "text", "text": question})

    # Keys not scoped to a workspace must name one via this header.
    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    client = Anthropic(
        default_headers={"anthropic-workspace-id": workspace} if workspace else None
    )
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT.format(profile=_profile_text()),
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()

    # Render text with numbered citation markers, then a source list.
    citations: list[dict] = []
    for block in response.content:
        if block.type != "text":
            continue
        print(block.text, end="")
        for cit in block.citations or []:
            citations.append({"title": cit.document_title, "quote": cit.cited_text})
            print(f" [{len(citations)}]", end="")
    print("\n")

    if citations:
        print("Sources:")
        for i, c in enumerate(citations, start=1):
            quote = " ".join(c["quote"].split())
            if len(quote) > 200:
                quote = quote[:200] + "…"
            print(f"  [{i}] {c['title']}\n      “{quote}”")
    print(f"\n{NOTE}")
