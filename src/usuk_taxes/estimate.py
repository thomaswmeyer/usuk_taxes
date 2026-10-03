"""US federal estimate (Form 1040, MFJ) from a YAML inputs file.

An independent check on the numbers entered into tax software, not tax
software itself. Inputs live in $USUK_PRIVATE_DIR/inputs_<year>.yaml; every
year constant below names the corpus source it was verified against.

Models: wages and RSU vests with workday sourcing (Treas. Reg. 1.861-4),
Form 1116 general and treaty re-sourced categories (paid basis, standard
deduction apportioned per line 3a), Schedule E with Form 8582 suspension,
CTC/ODC phase-out, and NIIT. Not modelled: AMT, passive-category FTC,
qualified dividend / long-term capital gain rates.
"""

import datetime as dt
import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Year constants, each verified against the corpus source named alongside.
CONSTANTS = {
    2025: {
        "std_deduction_mfj": (31500, "irs-i1040 Standard Deduction Worksheet"),
        # (lower bound of bracket, rate): irs-i1040 Tax Computation Worksheet, Section B
        "brackets_mfj": ([(0, 0.10), (23850, 0.12), (96950, 0.22), (206700, 0.24),
                          (394600, 0.32), (501050, 0.35), (751600, 0.37)],
                         "irs-i1040 Tax Computation Worksheet, Section B"),
        "ctc_per_child": (2200, "irs-i1040 What's New (CTC $2,200, $1,700 refundable)"),
        "odc_per_dependent": (500, "Schedule 8812"),
        "ctc_phaseout_mfj": (400000, "irs-i1040s8812 (MFJ $400,000)"),
        "niit_threshold_mfj": (250000, "IRC 1411 (not in corpus)"),
        "ads_residential_years": (30, "irs-pub-527 / 2024 Form 4562 (foreign residential, ADS)"),
        "capital_loss_limit": (3000, "Schedule D instructions"),
        "passive_mag_phaseout_end": (150000, "Form 8582 special allowance fully phased out"),
    }
}


@dataclass
class Line:
    label: str
    amount: float
    note: str = ""


@dataclass
class Estimate:
    lines: list[Line] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    values: dict[str, float] = field(default_factory=dict)

    def add(self, key: str, label: str, amount: float, note: str = "") -> float:
        self.values[key] = amount
        self.lines.append(Line(label, amount, note))
        return amount

    def section(self, title: str) -> None:
        self.lines.append(Line(f"## {title}", math.nan))


def _date(v) -> dt.date:
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


def _num(v, gaps: list[str], what: str) -> float:
    if v is None:
        gaps.append(what)
        return 0.0
    return float(v)


def workdays(start: dt.date, end: dt.date, holidays: set[dt.date], leave: set[dt.date]) -> list[dt.date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in holidays and d not in leave:
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def bracket_tax(taxable: float, brackets: list[tuple[float, float]]) -> float:
    tax = 0.0
    for i, (lower, rate) in enumerate(brackets):
        prev_rate = brackets[i - 1][1] if i else 0.0
        tax += (rate - prev_rate) * max(0.0, taxable - lower)
    return tax


def compute(inputs: dict) -> Estimate:
    year = int(inputs["tax_year"])
    c = {k: v[0] for k, v in CONSTANTS[year].items()}
    e = Estimate()
    gaps = e.gaps
    fx = float(inputs["fx_gbp_per_usd"])
    usd = lambda gbp: gbp / fx  # noqa: E731

    holidays = {_date(d) for d in inputs.get("bank_holidays", [])}
    wd = inputs["workdays"]
    leave = {_date(d) for d in wd.get("leave_dates") or []}
    if not wd.get("leave_dates_confirmed"):
        gaps.append("annual leave dates (workday denominators currently include leave)")
    us_dates = sorted(_date(d) for d in wd["us_dates"])

    def us_share(start, end):
        days = workdays(start, end, holidays, leave)
        us = sum(1 for d in us_dates if start <= d <= end)
        return (us / len(days) if days else 0.0), us, len(days)

    # ── Wages ──
    e.section("Wages (GBP converted at IRS yearly average)")
    wages_total = wages_us = own_emp_total = 0.0
    uk_tax_own = uk_tax_spouse = 0.0
    for w in inputs["wages"]:
        name = w["employer"]
        gross = _num(w.get("gross"), gaps, f"{name}: gross pay")
        if w.get("gross") is None:  # whole employment missing: one gap is enough
            pension = tax = 0.0
        else:
            pension = _num(w.get("employer_pension"), gaps, f"{name}: employer pension")
            tax = _num(w.get("uk_tax"), gaps, f"{name}: UK tax withheld")
        amount = usd(gross + pension)
        share, us, n = (0.0, 0, 0)
        if not w.get("spouse") and w.get("period"):
            start, end = (_date(x) for x in w["period"])
            share, us, n = us_share(start, end)
        note = f"US-source {us}/{n} workdays = {share:.2%}" if n else "all UK workdays"
        e.add(f"wages:{name}", f"{name} — wages incl. employer pension", amount, note)
        wages_total += amount
        wages_us += amount * share
        if w.get("spouse"):
            uk_tax_spouse += usd(tax)
        else:
            uk_tax_own += usd(tax)
            own_emp_total += amount

    # ── RSUs ──
    e.section("RSU vests (shares x vest-date FMV)")
    rsu_total = rsu_us = rsu_tax = 0.0
    start = _date(inputs["rsu_period_start"])
    for v in inputs["rsu_vests"]:
        vest = _date(v["vest"])
        amount = v["shares"] * v["fmv_usd"]
        share, us, n = us_share(start, vest)
        e.add(f"rsu:{vest}", f"Vest {vest}: {v['shares']} x ${v['fmv_usd']}", amount,
              f"US-source {us}/{n} workdays = {share:.2%} (${amount * share:,.0f})")
        rsu_total += amount
        rsu_us += amount * share
        rsu_tax += usd(float(v.get("uk_tax_paid_in_year") or 0))
    own_emp_total += rsu_total

    # ── Schedule E ──
    e.section("Schedule E — UK rental (100%, MFJ)")
    r = inputs["rental"]
    rent = usd(_num(r.get("rent"), gaps, "rental: rent"))
    expenses = usd(sum(_num(r.get(k), gaps, f"rental: {k.replace('_', ' ')}")
                       for k in ("management_fees", "repairs", "other_expenses", "insurance", "mortgage_interest")))
    depreciation = float(r["depreciation_basis_usd"]) / c["ads_residential_years"]
    net = e.add("sche_net", "Schedule E net income/(loss)", rent - expenses - depreciation,
                f"rent ${rent:,.0f} − expenses ${expenses:,.0f} − ADS depreciation ${depreciation:,.0f}")
    suspended = float(r.get("prior_suspended_loss_usd") or 0)
    allowed = 0.0 if net < 0 else max(0.0, net - suspended)
    e.add("sche_allowed", "Allowed after Form 8582", allowed,
          "loss fully suspended: MAGI well above $150k (no $25k allowance)")
    e.add("sche_carry", "Suspended passive loss carried to next year",
          suspended - net if net < 0 else max(0.0, suspended - net))

    # ── Other income ──
    e.section("Other income")
    o = inputs.get("other_income_usd", {})
    interest = _num(o.get("schwab_interest"), gaps, "Schwab interest") + \
        _num(o.get("uk_bank_interest"), gaps, "UK bank interest (USD)")
    cap = _num(o.get("short_term_capital_gain"), gaps, "capital gain/loss")
    cap_allowed = max(-c["capital_loss_limit"], cap)
    pension_growth = _num(o.get("foreign_pension_growth"), gaps, "foreign pension growth (s.402(b))")
    e.add("interest", "Interest", interest)
    e.add("capgain", "Capital gain/(loss) allowed", cap_allowed,
          f"net ${cap:,.2f}; carryforward ${cap_allowed - cap:,.2f}" if cap < cap_allowed else "")
    e.add("pension", "Foreign pension growth", pension_growth)

    # ── 1040 ──
    e.section("Form 1040")
    agi = e.add("agi", "Adjusted gross income",
                wages_total + rsu_total + allowed + interest + cap_allowed + pension_growth)
    std = c["std_deduction_mfj"]
    ti = e.add("ti", "Taxable income", max(0.0, agi - std), f"standard deduction ${std:,}")
    tax = e.add("tax", "Tax before credits", bracket_tax(ti, c["brackets_mfj"]))

    # ── Form 1116 ──
    e.section("Form 1116 (paid basis)")
    treaty_inc = wages_us + rsu_us
    # Foreign pension growth is UK-source compensation: general category.
    general_inc = wages_total + rsu_total - treaty_inc + pension_growth
    total_gross = wages_total + rsu_total + rent + interest + max(0.0, cap) + pension_growth
    cat_ti = {}
    for key, inc in (("general", general_inc), ("treaty_resourced", treaty_inc)):
        cat_ti[key] = inc - std * (inc / total_gross if total_gross else 0)
    # A net US-source loss reduces foreign-source income (s.904(g)): scale the
    # categories down pro rata so together they never exceed taxable income.
    if sum(cat_ti.values()) > ti > 0:
        scale = ti / sum(cat_ti.values())
        cat_ti = {k: v * scale for k, v in cat_ti.items()}
    uk_emp_tax = uk_tax_own + rsu_tax
    treaty_tax = uk_emp_tax * (treaty_inc / own_emp_total) if own_emp_total else 0.0
    general_tax = uk_emp_tax - treaty_tax + uk_tax_spouse
    carry = inputs.get("ftc_carryovers_usd", {})
    ftc_total = 0.0
    for key, label, paid in (("general", "General", general_tax),
                             ("treaty_resourced", "Treaty re-sourced (UK)", treaty_tax)):
        limit = tax * min(1.0, cat_ti[key] / ti) if ti else 0.0
        co = float(carry.get(key) or 0)
        allowed_c = min(limit, paid + co)
        ftc_total += allowed_c
        e.add(f"ftc_inc:{key}", f"{label}: income less apportioned std deduction", cat_ti[key])
        e.add(f"ftc_limit:{key}", f"{label}: limitation", limit)
        e.add(f"ftc_paid:{key}", f"{label}: UK tax paid in {year}", paid)
        e.add(f"ftc_allowed:{key}", f"{label}: credit allowed", allowed_c, f"carryover in ${co:,.0f}")
        e.add(f"ftc_carry:{key}", f"{label}: carryforward to {year + 1}", paid + co - allowed_c,
              "current-year tax is used before carryovers")
    ftc = e.add("ftc", "Total foreign tax credit", min(ftc_total, tax))

    # ── Credits and NIIT ──
    e.section("Child credits and NIIT")
    d = inputs.get("dependents", {})
    reduction = 50 * math.ceil(max(0.0, agi - c["ctc_phaseout_mfj"]) / 1000)
    ctc = e.add("ctc", "CTC + ODC after phase-out",
                max(0.0, c["ctc_per_child"] * d.get("ctc_children", 0)
                    + c["odc_per_dependent"] * d.get("other_dependents", 0) - reduction),
                f"phase-out reduction ${reduction:,}")
    nii = max(0.0, interest + cap_allowed + allowed)
    niit = e.add("niit", "Net investment income tax", 0.038 * min(nii, max(0.0, agi - c["niit_threshold_mfj"])),
                 f"NII ${nii:,.0f}; not reducible by the FTC")
    e.add("total", "Estimated total US tax", max(0.0, tax - ftc - ctc) + niit)
    return e


def render(e: Estimate, inputs_path: Path) -> str:
    out = [f"# US federal estimate — generated from {inputs_path.name}", ""]
    for line in e.lines:
        if math.isnan(line.amount):
            out += ["", line.label, "", "| Item | USD | Note |", "|---|---:|---|"]
        else:
            out.append(f"| {line.label} | {line.amount:,.0f} | {line.note} |")
    if e.gaps:
        out += ["", "## Missing inputs (treated as 0)", ""] + [f"- {g}" for g in e.gaps]
    return "\n".join(out) + "\n"


def run(inputs_path: Path) -> tuple[Estimate, str]:
    inputs = yaml.safe_load(inputs_path.read_text())
    e = compute(inputs)
    return e, render(e, inputs_path)
