# usuk-taxes

A retrieval-augmented tax research assistant for US expatriates living in the
UK. Downloads authoritative sources (IRS publications and form instructions,
HMRC guidance, the US-UK income tax treaty), indexes them locally, and answers
questions with Claude — every answer grounded in cited passages from the
corpus.

**Not professional tax advice.** It's a research and calculation aid; verify
anything high-stakes with a cross-border tax professional.

## Setup

```sh
uv sync
export ANTHROPIC_API_KEY=...   # needed for `ask` only
```

## Usage

```sh
uv run usuk fetch          # download the corpus (cached in corpus/raw/)
uv run usuk index          # extract, chunk, embed (local model), build index
uv run usuk ask "How are stock options from my US employer's parent company taxed while I work in the UK?"
uv run usuk sources        # list sources and cache status
```

Edit `profile.yaml` to describe the filing situation — it is injected into the
advisor's system prompt so answers are tailored. Edit
`corpus/manifest.yaml` to add sources, then re-run `fetch` and `index`.
