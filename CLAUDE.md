# usuk_taxes

RAG-based US/UK tax research assistant for a US citizen living in the UK,
built to help prepare the US federal return (TY 2025) and UK Self Assessment
(2025-26). Personal tool today; may be hosted for others later, so keep the
core library (`src/usuk_taxes/`) free of machine-specific assumptions.

## Architecture

- `corpus/manifest.yaml` — authoritative source list (IRS pubs/instructions,
  HMRC guidance, US-UK treaty). Add sources here, never hardcode URLs in code.
- `src/usuk_taxes/ingest.py` — download (cached in `corpus/raw/`) + text
  extraction (cached in `corpus/text/`).
- `src/usuk_taxes/chunking.py` → `index.py` — paragraph chunks; hybrid
  retrieval = Chroma (local ONNX embeddings, no API key) + BM25, fused with RRF.
- `src/usuk_taxes/advisor.py` — Claude call. Retrieved chunks are sent as
  document blocks with the API citations feature enabled; answers must cite.
- `profile.yaml` — the household tax situation, injected into the system
  prompt. Update it when facts change; it also lists open fact questions.

## Commands

- `uv sync` — install
- `uv run usuk fetch` / `index` / `ask "..."` / `sources`
- Requires `ANTHROPIC_API_KEY` for `ask` only; fetch/index are fully local.

## Conventions

- Corpus and index artifacts (`corpus/raw/`, `corpus/text/`, `data/`) are
  gitignored and reproducible; only the manifest is source of truth.
- Model: `claude-opus-4-8` (override with `USUK_MODEL`).
- Tax-content answers must always name the jurisdiction and tax year; the US
  and UK tax years are offset (calendar vs 6 Apr–5 Apr).
