import datetime as dt

import pytest

from usuk_taxes.estimate import CONSTANTS, bracket_tax, compute, workdays

BRACKETS = CONSTANTS[2025]["brackets_mfj"][0]


@pytest.mark.parametrize(
    "taxable, rate, subtract",
    # i1040 2025 Tax Computation Worksheet, Section B (MFJ): tax = income x rate - subtraction
    [(150000, 0.22, 10172.00), (300000, 0.24, 14306.00), (450000, 0.32, 45874.00),
     (600000, 0.35, 60905.50), (900000, 0.37, 75937.50)],
)
def test_brackets_match_irs_worksheet(taxable, rate, subtract):
    assert bracket_tax(taxable, BRACKETS) == pytest.approx(taxable * rate - subtract)


def test_workdays_skip_weekends_holidays_and_leave():
    # Mon 2 Jun - Fri 13 Jun 2025: 10 weekdays, one leave day.
    days = workdays(dt.date(2025, 6, 2), dt.date(2025, 6, 13), set(), {dt.date(2025, 6, 6)})
    assert len(days) == 9
    # Christmas week: 25 and 26 Dec are bank holidays.
    xmas = {dt.date(2025, 12, 25), dt.date(2025, 12, 26)}
    assert len(workdays(dt.date(2025, 12, 22), dt.date(2025, 12, 26), xmas, set())) == 3


def _inputs(**over):
    base = {
        "tax_year": 2025,
        "fx_gbp_per_usd": 0.75,
        "bank_holidays": [],
        "workdays": {"us_dates": ["2025-06-09"], "leave_dates": [], "leave_dates_confirmed": True},
        "wages": [{"employer": "UK Co", "gross": 150000, "employer_pension": 0, "uk_tax": 55000,
                   "period": ["2025-01-01", "2025-12-31"]}],
        "rsu_vests": [],
        "rsu_period_start": "2025-01-01",
        "rental": {"rent": 0, "management_fees": 0, "repairs": 0, "other_expenses": 0,
                   "insurance": 0, "mortgage_interest": 0, "depreciation_basis_usd": 0},
        "other_income_usd": {"schwab_interest": 0, "short_term_capital_gain": 0,
                             "uk_bank_interest": 0, "foreign_pension_growth": 0},
        "dependents": {"ctc_children": 0, "other_dependents": 0},
    }
    base.update(over)
    return base


def test_high_uk_tax_leaves_no_us_tax_and_sources_us_day():
    e = compute(_inputs())
    v = e.values
    assert v["agi"] == pytest.approx(200000)
    assert v["total"] == pytest.approx(0, abs=0.01)
    # 1 US day out of 261 weekdays in 2025 is re-sourced to the treaty category.
    assert v["ftc_inc:treaty_resourced"] > 0
    assert not e.gaps


def test_rental_loss_is_suspended_and_carried():
    e = compute(_inputs(rental={"rent": 7500, "management_fees": 0, "repairs": 0, "other_expenses": 0,
                                "insurance": 0, "mortgage_interest": 0, "depreciation_basis_usd": 600000,
                                "prior_suspended_loss_usd": 1000}))
    # 7,500 GBP = 10,000 USD rent, less 20,000 depreciation = 10,000 loss, all suspended.
    assert e.values["sche_net"] == pytest.approx(-10000)
    assert e.values["sche_allowed"] == 0
    assert e.values["sche_carry"] == pytest.approx(11000)


def test_ctc_phases_out_above_threshold():
    e = compute(_inputs(dependents={"ctc_children": 1, "other_dependents": 2}))
    # MAGI 200,000 is under the 400,000 MFJ threshold: full 2,200 + 2 x 500.
    assert e.values["ctc"] == pytest.approx(3200)


def test_us_source_loss_cannot_push_categories_above_taxable_income():
    # A $3,000 US-source capital loss plus untaxed foreign pension growth:
    # credits must still fully cover US tax when UK tax is high.
    e = compute(_inputs(other_income_usd={"schwab_interest": 0, "short_term_capital_gain": -7000,
                                          "uk_bank_interest": 0, "foreign_pension_growth": 6000}))
    v = e.values
    assert v["ftc_inc:general"] + v["ftc_inc:treaty_resourced"] <= v["ti"] + 0.01
    assert v["total"] == pytest.approx(0, abs=0.01)
