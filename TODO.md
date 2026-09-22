# TODO — status and plan as of 22 September 2026

Goal: use this tool to check the US federal TY 2025 filing plan before the
15 October 2026 extended deadline. UK Self Assessment 2025-26 is not due until
31 January 2027 and is secondary for now.

## Where the project stands

- Last commits: 6 July 2026 (three commits, nothing since). Scaffold is
  complete: `fetch`, `index`, `ask` (with API citations) and `workbook` are all
  implemented (~820 lines in `src/usuk_taxes/`).
- No tests and no retrieval evaluation. Nothing in git proves the end-to-end
  loop (fetch → index → ask) has been exercised; corpus and index are
  gitignored, so that state lives only on the local machine.
- Verified 22 Sep 2026: package installs, CLI runs, workbook generates, and
  every cross-sheet formula in the workbook lands on the row its label
  describes (row-counting layout intact).
- Not verified: whether the 40 manifest URLs still resolve. The remote
  sandbox used for the check blocks irs.gov and gov.uk, so fetch must be run
  locally. The gov.uk asset links (SA105 / SA106 / SA109 notes) embed a media
  hash and are the most likely to have rotted.

## Blockers to resolve first (facts, not code)

- [ ] Confirm Form 4868 was filed by 15 June 2026. The 15 October deadline
      only exists if it was; otherwise the return is already late. Any US
      balance has accrued interest since 15 April 2026 either way.
- [ ] Answer the open questions in `profile.yaml`: spouse's US status
      (MFJ vs MFS), ISO vs NQSO grants (AMT exposure), rental ownership
      split, FEIE vs FTC strategy. The first two change the shape of the
      whole return; every `ask` answer is only as good as these facts.
- [ ] FBAR (FinCEN 114) shares the 15 October automatic extension and
      Form 8938 rides with the return. Both instruction sets are in the
      corpus; neither deadline is in the workbook README.

## Getting the tool running locally

- [ ] `uv sync && uv run usuk fetch` — fix or replace any dead manifest URLs.
- [ ] `uv run usuk index` — first run downloads the local embedding model.
- [ ] Set `ANTHROPIC_API_KEY` (`.env` is gitignored and auto-loaded).
- [ ] Smoke-test `usuk ask --show-passages` on one question per topic
      (options sourcing, rental, FTC, treaty) and check the retrieved
      passages are actually relevant before trusting answers.

## Workbook constants to verify with `usuk ask`

Grey cells were entered from memory at generation time. Confirm against the
corpus before relying on any figure:

- [ ] IRS 2025 yearly average GBP/USD rate (FX sheet, currently 0.759)
- [ ] MFJ standard deduction 2025 (US FTC sheet, currently $31,500)
- [ ] FEIE limit 2025 (FEIE vs FTC sheet, currently $130,000)
- [ ] UK 2025-26 personal allowance / basic-rate band / additional-rate
      threshold (UK Tax sheet)

## Known gaps in the workbook

- "US tax before credits" is a manual input: there is no 2025 MFJ bracket
  calculation and no Child Tax Credit / ODC modelling. The FEIE-vs-FTC sheet
  is qualitative only; the US liability has to be computed by hand or in
  tax software.
- Only one (general-basket) Form 1116 is modelled. Net rental income is
  normally passive basket and needs a second limitation block, plus the
  high-tax kickout check.
- NIC is correctly excluded from creditable tax, but UK tax on rental income
  (paid via SA, not PAYE) is not yet fed into the FTC "tax paid" line.

## Questions worth putting to `usuk ask` for the filing plan

- Option/RSU spread sourcing by workdays over grant→vest (EIM43501,
  ERSM162000) and how the UK-source share flows to Form 1116.
- Treaty re-sourcing / saving clause interaction for the US-workday share.
- Passive vs general basket for the UK rental, and the high-tax kickout.
- Whether claiming the FTC (not FEIE) preserves the refundable CTC for
  qualifying children, and the ODC for older dependents.
- Paid vs accrued basis election on Form 1116 given the offset tax years.
- FBAR / Form 8938 thresholds for the UK accounts.

## If there is time to extend the code (in priority order)

1. 2025 MFJ bracket + CTC/ODC calculation feeding the US FTC sheet.
2. Second Form 1116 block for the passive basket.
3. FBAR / 8938 lines in the workbook README deadline list.
4. A `--save` option on `ask` to keep answers and citations for the file.
5. A smoke test that fetches one small source, indexes it and runs `search`.

Anything larger than this is unlikely to pay off before 15 October.
