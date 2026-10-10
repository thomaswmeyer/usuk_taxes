# usuk-taxes

A research tool for US citizens living in the UK who prepare their own US
federal return (and UK Self Assessment) and want answers they can check.

- **`usuk ask`** — cited research over a local corpus of authoritative
  sources: IRS publications and form instructions, key Treasury regulations,
  HMRC manuals and guidance, and the US-UK income tax treaty with its
  Technical Explanation. Answers come from Claude using the API's citations
  feature, so every claim is tied to a quoted passage, and it says when the
  sources don't cover something.
- **`usuk estimate`** — an independent US federal estimate (Form 1040,
  married filing jointly) from a YAML inputs file, to check what your tax
  software produces.

## Disclaimer

**This is a research tool, not tax, legal or financial advice.** It is not a
tax advisor and does not replace one.

- Its answers and estimates can be wrong, incomplete or out of date — tax law,
  forms and rates change, and the sources it retrieves may not cover your
  situation.
- You are solely responsible for your own tax returns and for checking
  anything you rely on against the cited sources or with a qualified
  cross-border tax professional.
- It is provided "as is", without warranty of any kind, under the MIT
  license; the authors accept no liability for any tax, penalty, interest or
  other loss arising from its use.
- It is not affiliated with or endorsed by the IRS, HMRC, the US Treasury,
  Intuit/TurboTax or Anthropic.

Every `ask` answer and `estimate` report ends with a one-line reminder of this.

## How it was used

Built with [Claude Code](https://claude.com/claude-code) to prepare a real
2025 return: UK salary, RSUs from a US parent company, a UK rental, foreign
tax credit carryovers and a treaty position. Claude Code read the household's
payslips, broker forms and prior-year returns from a private folder, filled in
the inputs file with a source for every figure, researched open questions with
`usuk ask`, and walked through the TurboTax entry. The estimate matched the
filed return to within $2.

The code is the smaller part of that; the workflow is the reusable idea. Use
this repo as a starting point and point it at your own documents.

## Setup

```sh
uv sync
cp .env.example .env    # or create .env by hand — see below
```

`.env` (gitignored) holds local settings:

```sh
ANTHROPIC_API_KEY=sk-ant-...            # needed for `ask` only
# ANTHROPIC_WORKSPACE_ID=wrkspc_...     # only if your key isn't workspace-scoped
USUK_PRIVATE_DIR=~/path/outside/the/repo
```

## Keeping personal data out of the repo

Everything personal lives in `USUK_PRIVATE_DIR`, a folder **outside** the
repository (a synced folder such as Dropbox works well):

| File | Purpose |
|---|---|
| `profile.yaml` | Your household facts, injected into `ask`'s system prompt so answers fit your situation. Start from `profile.example.yaml`. |
| `inputs_2025.yaml` | Figures for `usuk estimate`. Start from `examples/inputs_2025.example.yaml`. |
| `estimate_2025.md` | Written by `usuk estimate`. |

Source documents (returns, payslips, statements) stay wherever you keep them;
nothing needs copying into the repo. Corpus downloads and the search index are
gitignored and rebuildable.

## Usage

```sh
uv run usuk fetch          # download the corpus (cached in corpus/raw/)
uv run usuk index          # extract text, chunk, embed locally, build the index
uv run usuk ask "How are RSUs from my US employer's parent sourced when I work in the UK?"
uv run usuk ask --show-passages "..."   # also print the retrieved passages
uv run usuk estimate       # US estimate from $USUK_PRIVATE_DIR/inputs_2025.yaml
uv run usuk estimate --inputs examples/inputs_2025.example.yaml   # try it with fictional data
uv run usuk sources        # list sources and cache status
```

`fetch`, `index` and `estimate` run locally with no API key; retrieval uses a
small local embedding model plus BM25. Only `ask` calls the Claude API.

To add a source, add it to `corpus/manifest.yaml` and re-run `fetch` and
`index`.

## What the estimate covers

US tax year 2025, married filing jointly:

- Wages from UK employers (including employer pension contributions), and
  RSU vests at vest-date value.
- **Workday sourcing** of salary and RSUs (Treas. Reg. 1.861-4) from a list of
  US workdays, leave days and bank holidays.
- **Form 1116** on the paid basis with a general category and a treaty
  re-sourced category (US-UK treaty Art. 24(6)); standard deduction
  apportioned; prior-year carryovers. (Form 8833 isn't needed for this
  position — Treas. Reg. 301.6114-1(c)(1)(v).)
- **Schedule E** for a UK rental with ADS 30-year depreciation and Form 8582
  passive-loss suspension.
- Capital loss limit, child tax credit / credit for other dependents
  phase-out, and net investment income tax.

Not covered: other filing statuses, other tax years, AMT, the passive Form
1116 category, qualified dividend / long-term gain rates, the foreign earned
income exclusion, and any UK Self Assessment calculation. Each year constant
in `src/usuk_taxes/estimate.py` names the corpus source it was checked
against.

## Tests

```sh
uv run --with pytest pytest tests/
```

The tests use synthetic data only; the bracket tests check against the IRS
2025 Tax Computation Worksheet.

## Other files

- `usuk workbook` generates an older Excel scaffold
  (`spreadsheets/template_2025.xlsx`); `usuk estimate` supersedes it.
- `ROADMAP.md` lists what's missing.

## License

MIT — see `LICENSE`.
