# Roadmap

What's missing, roughly in order of usefulness to other US-in-UK filers.

## Estimate
- **UK Self Assessment calculation** (2025-26): employment income incl. RSUs
  and the ITEPA s.428A deduction for transferred employer NIC, property
  income with the 20% finance-cost credit, self-employment, Foreign Tax
  Credit Relief.
- **Other filing statuses** (single, married filing separately) and a
  non-US-person spouse.
- **Constants by year**: `CONSTANTS` is keyed by year but only 2025 exists.
- **Passive-category Form 1116** for a rental that turns profitable, and the
  high-tax kickout.
- **AMT** and the AMT foreign tax credit.
- **Qualified dividend / long-term capital gain rates.**
- **Accrued-basis foreign taxes**, including the UK/US tax-year mismatch.
- Validate the inputs file against a schema and report unknown keys.

## Research assistant
- An evaluation set: questions with known answers and the passages they must
  cite, to catch retrieval regressions when the corpus changes.
- HMRC manual pages on use of home and on trading losses (BIM47800+,
  BIM75000+, HS227) for self-employment questions.
- Detect when a gov.uk "current year" page has rolled over to the next tax
  year (it happened to the income tax rates page).
- `ask --save` to keep answers and citations alongside the inputs.

## Data import
- Parsers for common UK payslip PDFs, OFX/QBO bank exports and broker 1099
  composites, so the inputs file can be filled semi-automatically.
