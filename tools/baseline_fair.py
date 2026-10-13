"""The fair rules baseline: policy sections 5, 6, 7 and 10 coded as deterministic rules.

This is what a competent engineer would build from the policy without a language model:
normalised invoice numbers, client aliases and shared name words, bank-charge caps, exact
sums of open invoices, stated part payments, the ordered decline rules on the structured
fields, and phrase rules with negation handling and date parsing for client replies.
It was written from agent/policy.md only, never from the answer keys.

Output shapes match tools/baseline.py exactly, with "ask" where the naive baseline says "unmatched".

Standard library only, Python 3.9 compatible. Run: python3 tools/baseline_fair.py
"""
import calendar
import itertools
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / "eval" / "inputs"
OUT = ROOT / "eval" / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

DEFAULT_BASE = date(2026, 10, 9)  # the blind test's reply date, a Friday


# ----------------------------------------------------------------------------
# Section 5: matching a payment to invoices
# ----------------------------------------------------------------------------

CHARGE_CAP = {"USD": 50.0, "GBP": 40.0, "EUR": 45.0}
CHARGE_PCT = 0.03
EPS = 0.005

# Legal-form and connector words carry no identity; they are dropped before comparing names.
SUFFIX_WORDS = {
    "INC", "LTD", "LIMITED", "LLC", "LLP", "LP", "PLC", "PLLC", "GMBH", "AG", "BV", "NV", "SA", "SAS", "SARL",
    "SL", "SRL", "PTE", "PTY", "CO", "CORP", "CORPORATION", "COMPANY", "KG", "OY", "AB", "SPA", "SRO",
    "AND", "EN", "UND", "ET", "Y", "THE", "OF",
}
# Words too generic to identify a client on their own.
GENERIC_WORDS = {
    "GROUP", "HOLDING", "HOLDINGS", "INTERNATIONAL", "GLOBAL", "SERVICES", "SOLUTIONS", "PARTNERS", "CAPITAL",
    "CONSULTING", "MEDIA", "LABS", "STUDIO", "STUDIOS", "SOFTWARE", "SYSTEMS", "ANALYTICS", "DIGITAL",
    "TECHNOLOGIES", "TECHNOLOGY", "DESIGN", "LEARNING", "HEALTH", "RETAIL", "TRADING", "VENTURES", "PAYMENTS",
    "PAYABLES", "TREASURY", "NEW", "YORK", "NORTH", "SOUTH", "EAST", "WEST", "UK", "US", "USA", "EUROPE",
}

REFUND_RE = re.compile(
    r"\b(refund|money back|send (?:\S+ ){0,6}back|return (?:the |our )?(?:payment|money|funds)|reimburs|chargeback|"
    r"pay ?back|rembours|erstatt|r[üu]ckzahl|reembols|devoluci|terugbetal|retourn)",
    re.I,
)
PART_WORD_RE = re.compile(
    r"\b(PART|PARTIAL|ADVANCE|INSTALMENT|INSTALLMENT|PAGO PARCIAL|PARCIAL|ANTICIPO|ANZAHLUNG|TEILZAHLUNG|"
    r"ABSCHLAG|AKONTO|ACOMPTE|DEELBETALING|AANBETALING|VOORSCHOT)\b"
)
PCT_RE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s?%")
N_OF_M_RE = re.compile(r"\b(\d)\s+(?:OF|VON|DE|VAN)\s+(\d)\b")


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def fix_o(s):
    """Turn the letter O into a zero when it sits inside a run of digits (SL-1O47 -> SL-1047)."""
    s = (s or "").upper()
    while True:
        new = re.sub(r"(?<=\d)O|O(?=\d)", "0", s)
        if new == s:
            return s
        s = new


def name_words(s):
    s = (s or "").upper().replace("&", " AND ").replace(".", "")
    return [w for w in re.split(r"[^A-Z0-9]+", s) if w and w not in SUFFIX_WORDS]


def core(s):
    return "".join(name_words(s))


def distinctive(s):
    """The first word of a name that is neither a legal form nor a generic business word."""
    for w in name_words(s):
        if w not in GENERIC_WORDS and len(w) >= 3:
            return w
    ws = name_words(s)
    return ws[0] if ws else ""


def cents(x):
    return int(round(float(x) * 100))


def tied_clients(case):
    """Clients the payer can be tied to, strongest tier first: exact name or alias, then the client
    named in the reference (payment services), then a shared distinctive name word."""
    p = case["payment"]
    payer = p.get("payer_name") or ""
    ref = p.get("reference") or ""
    clients = []
    for inv in case["open_and_recent_invoices"]:
        if inv["client"] not in clients:
            clients.append(inv["client"])
    aliases = case.get("known_payer_aliases") or {}
    payer_core, payer_norm = core(payer), norm(payer)
    payer_words = set(name_words(payer))

    tier1 = []
    for c in clients:
        names = [c] + list(aliases.get(c, []))
        if any(payer_core and (payer_core == core(n) or payer_norm == norm(n)) for n in names):
            tier1.append(c)
    if tier1:
        return tier1, "payer name or known alias"

    ref_core = core(ref)
    ref_words = set(name_words(ref))
    tier2_full = [c for c in clients
                  if any(len(core(n)) >= 5 and core(n) in ref_core for n in [c] + list(aliases.get(c, [])))]
    if tier2_full:
        return tier2_full, "client named in the reference"
    tier2_word = [c for c in clients if distinctive(c) and distinctive(c) in ref_words]
    if tier2_word:
        return tier2_word, "client name word in the reference"

    tier3 = [c for c in clients if distinctive(c) and distinctive(c) in payer_words]
    if tier3:
        return tier3, "payer shares the client's distinctive name word"
    return [], ""


def referenced_invoices(ref, invoices):
    fixed = fix_o(ref)
    n = norm(fixed)
    tokens = re.findall(r"[A-Z]+|\d+", fixed)
    digit_tokens = set(t for t in tokens if t.isdigit())
    found = []
    for inv in invoices:
        num = inv["invoice"].upper()
        digits = re.sub(r"\D", "", num)
        if (norm(num) and norm(num) in n) or (len(digits) >= 3 and digits in digit_tokens):
            found.append(inv)
    return found


def part_payment(ref):
    """None when no part payment is stated; otherwise a dict with the stated fraction (or None)."""
    fixed = fix_o(ref)
    frac = None
    m = PCT_RE.search(fixed)
    if m:
        frac = float(m.group(1).replace(",", ".")) / 100.0
    m2 = N_OF_M_RE.search(fixed)
    if m2 and int(m2.group(2)) > 0:
        frac = 1.0 / int(m2.group(2))
    if PART_WORD_RE.search(fixed) or m or m2:
        return {"fraction": frac}
    return None


def within_charge(inv, amt):
    short = inv["amount"] - amt
    cap = CHARGE_CAP.get(inv["currency"], 0.0)
    return EPS < short <= cap + EPS and short <= CHARGE_PCT * inv["amount"] + EPS


def exact_subsets(invs, amt, min_size, max_size):
    """Subsets of open invoices of one client whose amounts sum exactly to the payment."""
    target = cents(amt)
    out = []
    for k in range(min_size, min(max_size, len(invs)) + 1):
        for combo in itertools.combinations(invs, k):
            if len(set(i["client"] for i in combo)) != 1:
                continue
            if sum(cents(i["amount"]) for i in combo) == target:
                out.append(list(combo))
    return out


def charge_subsets(invs, amt, min_size, max_size):
    """Subsets of open invoices of one client whose total is short by no more than a typical bank charge."""
    out = []
    for k in range(min_size, min(max_size, len(invs)) + 1):
        for combo in itertools.combinations(invs, k):
            if len(set(i["client"] for i in combo)) != 1:
                continue
            total = {"amount": sum(i["amount"] for i in combo), "currency": combo[0]["currency"]}
            if within_charge(total, amt):
                out.append(list(combo))
    return out


def part_candidates(invs, amt, part):
    bigger = [i for i in invs if i["amount"] > amt + EPS]
    if part and part.get("fraction"):
        f = part["fraction"]
        bigger = [i for i in bigger if abs(i["amount"] * f - amt) <= 1.0]
    return bigger


def match_rule(case):
    cid = case["id"]
    p = case["payment"]
    cur = p["currency"]
    amt = round(float(p["amount"]), 2)
    invs = case["open_and_recent_invoices"]
    ref = p.get("reference") or ""

    def link(chosen, reason):
        return {"id": cid, "decision": "link", "invoices": [i["invoice"] for i in chosen], "reason": reason}

    def ask(reason):
        return {"id": cid, "decision": "ask", "invoices": [], "reason": reason}

    # Section 10: a reference asking for money back is not a payment for an invoice.
    if REFUND_RE.search(ref):
        return ask("Reference asks for money back; bank transfers cannot be refunded through Razorpay")

    part = part_payment(ref)
    tied, how = tied_clients(case)
    referenced = referenced_invoices(ref, invs)

    if referenced:
        ref_clients = set(i["client"] for i in referenced)
        if tied and not (ref_clients & set(tied)):
            return ask("Reference names an invoice of a different client from the payer")
        open_ref = [i for i in referenced if i["status"] == "open" and i["currency"] == cur]
        paid_ref = [i for i in referenced if i["status"] != "open"]
        if not open_ref:
            if paid_ref:
                return ask("The only invoice the reference names is already paid; possible duplicate")
            return ask("Referenced invoice is in a different currency")
        # Extra words never widen a match: link only the referenced invoices the amount supports.
        subsets = exact_subsets(open_ref, amt, 1, 4)
        if len(subsets) == 1:
            return link(subsets[0], "Reference names the invoice(s) and the amount is exact")
        if len(subsets) > 1:
            return ask("Two or more referenced invoices fit the amount equally well")
        short_sets = charge_subsets(open_ref, amt, 1, 4)
        if len(short_sets) == 1:
            return link(short_sets[0], "Reference names the invoice(s); short by a typical bank charge")
        if len(short_sets) > 1:
            return ask("Two or more referenced invoices fit the amount within a bank charge")
        if len(set(i["client"] for i in open_ref)) > 1:
            return ask("Referenced invoices belong to different clients; a payment is never split across clients")
        if len(open_ref) == 1:
            inv = open_ref[0]
            if part and amt < inv["amount"] - EPS:
                frac = part.get("fraction")
                if frac and abs(inv["amount"] * frac - amt) > 1.0:
                    return ask("Stated percentage does not agree with the referenced invoice amount")
                return link([inv], "Reference names the invoice and states a part payment")
            if amt > inv["amount"] + EPS:
                same_client = [i for i in invs if i["client"] == inv["client"] and i["status"] == "open"
                               and i["currency"] == cur]
                combos = [c for c in exact_subsets(same_client, amt, 2, 3) if inv in c]
                if len(combos) == 1:
                    return link(combos[0], "Reference names one invoice; amount is the exact sum with other open invoices")
        if paid_ref and sum(cents(i["amount"]) for i in referenced if i["currency"] == cur) == cents(amt):
            return ask("Reference includes an invoice that is already paid; possible duplicate")
        if any(i["status"] != "open" and abs(i["amount"] - amt) < EPS for i in referenced):
            return ask("Amount matches an already-paid invoice; possible duplicate")
        if part:
            return ask("Part payment stated against several referenced invoices; which one is unclear")
        return ask("Amount differs from the referenced invoice(s) by more than a bank charge and no part payment is stated")

    if not tied:
        return ask("Payer cannot be tied to any client")

    cand_open = [i for i in invs if i["client"] in tied and i["status"] == "open" and i["currency"] == cur]
    cand_paid = [i for i in invs if i["client"] in tied and i["status"] != "open" and i["currency"] == cur]

    exact = [i for i in cand_open if abs(i["amount"] - amt) < EPS]
    if len(exact) == 1:
        return link(exact, "Payer tied to the client (%s) and the amount is exact" % how)
    if len(exact) > 1:
        return ask("Two or more open invoices of this client fit the amount equally well")

    combos = exact_subsets(cand_open, amt, 2, 3)
    if len(combos) == 1:
        return link(combos[0], "Payer tied to the client (%s); amount is the exact sum of open invoices" % how)
    if len(combos) > 1:
        return ask("Two or more combinations of open invoices fit the amount equally well")

    short = [i for i in cand_open if within_charge(i, amt)]
    if len(short) == 1:
        return link(short, "Payer tied to the client (%s); short by a typical bank charge" % how)
    if len(short) > 1:
        return ask("Two or more open invoices fit the amount within a bank charge")

    if part:
        cands = part_candidates(cand_open, amt, part)
        if len(cands) == 1:
            return link(cands, "Payer tied to the client (%s); stated part payment of one open invoice" % how)
        return ask("Part payment stated but it cannot be tied to a single open invoice")

    if any(abs(i["amount"] - amt) < EPS for i in cand_paid):
        return ask("The only matching invoice is already paid; possible duplicate")
    return ask("Amount differs from every candidate by more than a bank charge and no part payment is stated")


# ----------------------------------------------------------------------------
# Shared text helpers: quoted mail, dates, disputes
# ----------------------------------------------------------------------------

QUOTE_HEADER_RE = re.compile(
    r"^\s*(On .+ wrote:|Am .+ schrieb.*:|Le .+ a écrit\s*:|El .+ escribió\s*:|Op .+ schreef.*:|"
    r"-+\s*Original Message\s*-+|From:\s.+|Von:\s.+|De\s?:\s.+|Van:\s.+)\s*$",
    re.M,
)


def strip_quotes(text):
    """Keep only the latest message: drop quoted lines and everything after a quote header."""
    text = text or ""
    m = QUOTE_HEADER_RE.search(text)
    if m:
        text = text[: m.start()]
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(">")).strip()


MONTHS = {}
for _i, _names in enumerate([
    ["january", "jan", "januar", "enero", "ene", "janvier", "janv", "januari"],
    ["february", "feb", "februar", "febrero", "février", "fevrier", "févr", "februari"],
    ["march", "mar", "märz", "maerz", "marzo", "mars", "maart", "mrz"],
    ["april", "apr", "abril", "avril", "avr"],
    ["may", "mai", "mayo", "mei"],
    ["june", "jun", "juni", "junio", "juin"],
    ["july", "jul", "juli", "julio", "juillet", "juil"],
    ["august", "aug", "agosto", "août", "aout", "augustus"],
    ["september", "sept", "sep", "septiembre", "setiembre", "septembre"],
    ["october", "oct", "oktober", "okt", "octubre", "octobre"],
    ["november", "nov", "noviembre", "novembre"],
    ["december", "dec", "dezember", "dez", "diciembre", "dic", "décembre", "decembre", "déc"],
]):
    for _n in _names:
        MONTHS[_n] = _i + 1
MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

WEEKDAYS = {}
for _i, _names in enumerate([
    ["monday", "montag", "lunes", "lundi", "maandag"],
    ["tuesday", "dienstag", "martes", "mardi", "dinsdag"],
    ["wednesday", "mittwoch", "miércoles", "miercoles", "mercredi", "woensdag"],
    ["thursday", "donnerstag", "jueves", "jeudi", "donderdag"],
    ["friday", "freitag", "viernes", "vendredi", "vrijdag"],
    ["saturday", "samstag", "sonnabend", "sábado", "sabado", "samedi", "zaterdag"],
    ["sunday", "sonntag", "domingo", "dimanche", "zondag"],
]):
    for _n in _names:
        WEEKDAYS[_n] = _i
WEEKDAY_ALT = "|".join(sorted(WEEKDAYS, key=len, reverse=True))

DAY_MONTH_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th|er|º|\.)?\s*(?:de\s+|of\s+)?(" + MONTH_ALT + r")\b\.?(?:\s*,?\s*(\d{4}))?", re.I)
MONTH_DAY_RE = re.compile(r"\b(" + MONTH_ALT + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s*(\d{4}))?", re.I)
ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
NUMERIC_RE = re.compile(r"(?<![\d.])(\d{1,2})[./](\d{1,2})(?:[./](\d{4}|\d{2}))?(?![\d/])")
BARE_DAY_RE = re.compile(
    r"\b(?:the|den|am|on the)\s+(\d{1,2})(?:st|nd|rd|th|\.(?!\d))(?!\s*(?:" + MONTH_ALT + r"|%|[./]\d))", re.I)
WEEKDAY_DAY_RE = re.compile(
    r"\b(" + WEEKDAY_ALT + r")\s*,?\s*(?:the\s+|den\s+|el\s+|le\s+)?(\d{1,2})(?:st|nd|rd|th|\.(?!\d))?\b(?!\s*(?:"
    + MONTH_ALT + r"|%|[./]\d|hours|days))", re.I)
FIRST_WORKING_RE = re.compile(
    r"\b(?:first|1st|erste[nr]?|primer|premier|eerste)\s+(?:working|business|working|arbeits|laborable|ouvré|ouvrable|werk)\s*-?\s*(?:day|tag|día|dia|jour|dag)\s+(?:of|im|de|du|van)\s+(" + MONTH_ALT + r")\b", re.I)
END_OF_MONTH_RE = re.compile(r"\b(?:end|close) of (?:the |this )?month\b|\bmonth[- ]end\b|\bende des monats\b|\bfin de mes\b|\bfin du mois\b|\beind van de maand\b", re.I)
END_OF_NAMED_RE = re.compile(r"\b(?:end|close) of (" + MONTH_ALT + r")\b", re.I)
WEEKDAY_RE = re.compile(r"\b(" + WEEKDAY_ALT + r")\b", re.I)
HOLIDAY_RE = re.compile(r"\b((?:the )?(?:day|week) (?:after|before) )?(thanksgiving|christmas|new year(?:'s)?(?: day)?|boxing day)\b", re.I)


def holiday_date(name, base):
    """A few fixed-date holidays clients name as payment days; the next occurrence on or after the base date."""
    name = name.lower()
    for year in (base.year, base.year + 1):
        if name.startswith("thanksgiving"):
            first = date(year, 11, 1)
            d = first + timedelta(days=(3 - first.weekday()) % 7 + 21)  # fourth Thursday of November
        elif name.startswith("christmas"):
            d = date(year, 12, 25)
        elif name.startswith("boxing"):
            d = date(year, 12, 26)
        else:
            d = date(year, 1, 1)
        if d >= base:
            return d
    return None
PAST_BEFORE_RE = re.compile(r"\b(last|past|this past|el|le|letzten|letzte|vorigen|vorige|afgelopen|vergangenen)\s*$", re.I)
PAST_AFTER_RE = re.compile(r"^\s*(pasado|dernier|dernière|last)\b", re.I)


def _safe_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _resolve_bare_day(day, base):
    y, m = base.year, base.month
    if day < base.day:
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return _safe_date(y, m, day)


def _year_for(month, day, base):
    d = _safe_date(base.year, month, day)
    if d and d < base - timedelta(days=180):
        d = _safe_date(base.year + 1, month, day)
    return d


def find_dates(text, base):
    """All dates in the text as (position, date, kind) with kind 'explicit', 'weekday' or 'relative'."""
    t = text or ""
    low = t.lower()
    found = []
    taken = []

    def add(m, d, kind):
        if d is None:
            return
        for a, b in taken:
            if m.start() < b and m.end() > a:
                return
        taken.append((m.start(), m.end()))
        found.append((m.start(), d, kind))

    for m in FIRST_WORKING_RE.finditer(low):
        mon = MONTHS[m.group(1)]
        d = _year_for(mon, 1, base)
        while d and d.weekday() >= 5:
            d += timedelta(days=1)
        add(m, d, "explicit")
    for m in ISO_RE.finditer(low):
        add(m, _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "explicit")
    for m in DAY_MONTH_RE.finditer(low):
        day, mon = int(m.group(1)), MONTHS[m.group(2)]
        yr = int(m.group(3)) if m.group(3) else None
        add(m, _safe_date(yr, mon, day) if yr else _year_for(mon, day, base), "explicit")
    for m in MONTH_DAY_RE.finditer(low):
        mon, day = MONTHS[m.group(1)], int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else None
        add(m, _safe_date(yr, mon, day) if yr else _year_for(mon, day, base), "explicit")
    for m in NUMERIC_RE.finditer(low):
        a, b = int(m.group(1)), int(m.group(2))
        yr = m.group(3)
        if 1 <= b <= 12 and 1 <= a <= 31:
            day, mon = a, b
        elif 1 <= a <= 12 and 1 <= b <= 31:
            day, mon = b, a
        else:
            continue
        if yr:
            y = int(yr)
            y = y + 2000 if y < 100 else y
            add(m, _safe_date(y, mon, day), "explicit")
        else:
            add(m, _year_for(mon, day, base), "explicit")
    for m in END_OF_NAMED_RE.finditer(low):
        mon = MONTHS[m.group(1)]
        y = base.year if mon >= base.month else base.year + 1
        add(m, date(y, mon, calendar.monthrange(y, mon)[1]), "explicit")
    for m in WEEKDAY_DAY_RE.finditer(low):
        add(m, _resolve_bare_day(int(m.group(2)), base), "explicit")
    for m in BARE_DAY_RE.finditer(low):
        add(m, _resolve_bare_day(int(m.group(1)), base), "explicit")
    for m in HOLIDAY_RE.finditer(low):
        d = holiday_date(m.group(2), base)
        shift = re.sub(r"^the\s+", "", (m.group(1) or "").strip())
        if d and shift.startswith("day after"):
            d += timedelta(days=1)
        elif d and shift.startswith("day before"):
            d -= timedelta(days=1)
        elif d and shift.startswith("week after"):
            d += timedelta(days=7)
        add(m, d, "explicit")
    for m in END_OF_MONTH_RE.finditer(low):
        add(m, date(base.year, base.month, calendar.monthrange(base.year, base.month)[1]), "relative")
    for m in re.finditer(r"\b(tomorrow|morgen|mañana|demain)\b", low):
        add(m, base + timedelta(days=1), "relative")
    for m in WEEKDAY_RE.finditer(low):
        before = low[max(0, m.start() - 12): m.start()]
        after = low[m.end(): m.end() + 12]
        if PAST_BEFORE_RE.search(before) and PAST_AFTER_RE.search(after):
            continue
        if PAST_AFTER_RE.search(after) or re.search(r"\b(last|past|letzten|vorige|afgelopen)\s*$", before):
            continue
        wd = WEEKDAYS[m.group(1).lower()]
        ahead = (wd - base.weekday()) % 7
        if ahead == 0:
            ahead = 7
        add(m, base + timedelta(days=ahead), "weekday")
    found.sort(key=lambda x: x[0])
    return found


def pay_date(text, base):
    """The date a client says they will pay: the first explicit future date, else a weekday, else a relative one."""
    dates = find_dates(text, base)
    for kind in ("explicit", "weekday", "relative"):
        for _, d, k in dates:
            if k == kind and d >= base:
                return d
    return None


RETURN_WORDS_RE = re.compile(r"\b(back|return|returning|again|ab|wieder|erreichbar|retour|partir|desde|vuelvo|regreso|terug|vanaf|from)\b", re.I)
UNTIL_WORDS_RE = re.compile(r"\b(until|till|through|thru|bis|jusqu|hasta|tot|t/m|einschlie)", re.I)


def return_date(text, base):
    """An out-of-office return date: prefer a date after a 'back' word, then an 'until' date, then the first.
    Explicit dates outrank bare weekday names (a weekday usually just labels the explicit date beside it)."""
    dates = [x for x in find_dates(text, base) if x[2] != "relative"]
    explicit = [x for x in dates if x[2] == "explicit"]
    pool = explicit or dates
    low = (text or "").lower()
    ret, until, first = None, None, None
    for pos, d, kind in pool:
        window = low[max(0, pos - 32): pos]
        if ret is None and RETURN_WORDS_RE.search(window):
            ret = d
        elif until is None and UNTIL_WORDS_RE.search(window):
            until = d
        if first is None:
            first = d
    return ret or until or first


NEGATED_DISPUTE_RE = re.compile(
    r"(?:\b(?:not|no|never|without|nothing to|aren't|isn't|am not|are not|is not|don't|doesn't|didn't|won't)|n't)"
    r"\s+(?:\w+\s+){0,2}disput\w*|"
    r"\bdisput\w*\s+(?:nothing|none|nada|nichts|niets|rien)\b", re.I)
DISPUTE_RE = re.compile(
    r"\bdisput|\bnot paying\b|\bwon't (?:be )?pay|\bwill not (?:be )?pay|\brefuse to pay|\bdecline to pay|\bnot going to pay|"
    r"\bnot comfortable paying|\bnot happy (?:to pay|paying)|\bamount is wrong|\bwrong amount|\bincorrect amount|"
    r"\bovercharg|\boverbill|\bhours? (?:are|were|is|was) (?:wrong|incorrect|too high)|\bhours (?:\w+ ){0,3}corrected|"
    r"\bdon't agree|\bdo not agree|\bdisagree|\bnot agreed|\bwe agreed (?:\w+ ){0,4}not\b|"
    r"\bhours\b.{0,40}\b(?:nobody|no one|never|not|didn't|weren't|wasn't)\b.{0,40}\bwork|\bdouble what we agreed|"
    r"\b(?:twice|double|more than) what we (?:agreed|quoted|signed)|\bnot (?:the )?(?:amount|price|rate) we agreed|"
    r"\bdoes(?:n't| not) match (?:the |our )?(?:quote|contract|po\b|order|agreement|proposal)|"
    r"\bnot what we agreed|\bas it stands|\bbelong on our bill|\binvoice reflects|\binvoice is corrected|"
    r"\brevised invoice|\bcredit note|\bnot received the work|\bhaven't received the work|"
    r"\bwork (?:is|was) (?:not|never) (?:delivered|done|completed)|\bnever signed off|\bnot signed off|"
    r"\bonly signed off|\bdidn't sign off|\bnot delivered|\bcrash|\bbroken|\bdoesn't work|\bdoes not work|"
    r"\bnot working|\bactually works|\bfull price for|\bunusable|\bdefect|\bfaulty|\bhold until we|\buntil we've talked|"
    r"\bcontest(?:ing|ed|s|e|ons|é)?\b|\bchallenge the|\bquality (?:issue|problem)|\bshould(?:n't| not) (?:be )?(?:billed|charged)|"
    # German
    r"\bnicht (?:be)?zahlen|\bzahlen wir nicht|\bzahlen wir nichts|\bnie abgenommen|\bnicht abgenommen|"
    r"\bnicht einverstanden|\bstimmt nicht|\bstimmen nicht|\bzu hoch|\breklam|\bbeanstand|\bwiderspr|\bklären sie das zuerst|"
    # Spanish
    r"\bno (?:vamos a |lo |la )?pagar(?:emos)?\b|\bno pagaremos|\bno estamos de acuerdo|\bincorrect[oa]\b|\breclamaci|"
    r"\bno corresponde|\bimpugn|\berr[óo]neo|"
    # French
    r"\bne (?:paierons|payerons|paierai|paie) pas|\bne pas payer|\bpas d'accord|\bmontant (?:est )?(?:erron|incorrect)|"
    r"\berreur de facturation|\bne correspond pas|\blitige|\bréclam|"
    # Dutch
    r"\bbetalen (?:we|wij) niet|\bniet betalen|\bniet akkoord|\bklopt niet|\bkloppen niet|\bherkennen ons niet|"
    r"\bbetwist|\bte hoog|\bbezwaar|\bniet mee eens",
    re.I,
)


def is_dispute(text):
    t = NEGATED_DISPUTE_RE.sub(" ", text or "")
    return bool(DISPUTE_RE.search(t))


# ----------------------------------------------------------------------------
# Section 6: after a declined card payment
# ----------------------------------------------------------------------------

BANK_BLOCK_RE = re.compile(
    r"do not hono|don't hono|honou?r|cross.?border|\brisk\b|fraud|international|restricted|domestic|not permitted|"
    r"not allowed|blocked|locked|repeated attempts|attempt limit|generic decline|code 05|\(05\)|response 05|"
    r"pick.?up card|stolen|suspect|security", re.I)
AUTH_RE = re.compile(
    r"3.?d.?s|authenticat|enrol|one.?time pass|\botp\b|passcode|secure verification|cardholder verification|"
    r"challenge|\bsca\b|strong customer|secure code", re.I)
ADDRESS_RE = re.compile(r"\bavs\b|address|postcode|post code|postal code|\bzip\b|billing", re.I)
FUNDS_RE = re.compile(r"insufficient|limit|funds|balance|\(51\)|\(61\)|exceeds", re.I)
MERCHANT_RE = re.compile(r"merchant", re.I)
AVS_COUNTRIES = {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA", "GB", "UK", "UNITED KINGDOM", "CA", "CANADA"}
TRANSFER_RE = re.compile(r"\bwire|\bach\b|\bsepa\b|transfer|faster payment|\bbank\b|überweis|ueberweis|virement|transferencia|overboeking|overgemaakt|bonifico", re.I)
NEGATION_RE = re.compile(r"\b(never|none|not|no|nie|nicht|jamais|nunca|nooit|geen)\b", re.I)


def paid_by_transfer_before(history):
    clauses = re.split(r"[.;,]|\band\b|\bbut\b", history or "", flags=re.I)
    for cl in clauses:
        if NEGATION_RE.search(cl):
            continue
        if TRANSFER_RE.search(cl):
            return True
    return False


def parse_base(s):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))) or DEFAULT_BASE
    return DEFAULT_BASE


def decline_rule(case):
    cid = case["id"]
    reply = strip_quotes(case.get("client_reply") or "")
    base = parse_base(case.get("reply_date"))
    msg = case.get("decline_message") or ""

    def route(r):
        return {"id": cid, "route": r}

    if reply and is_dispute(reply):
        return route("stop_dispute")
    if case.get("do_not_contact"):
        return route("owner_sends")
    if (case.get("reminders_sent") or 0) >= 2:
        return route("hand_to_owner_limit")
    if reply and pay_date(reply, base):
        return route("wait_until_date")
    if case.get("merchant_international_cards_enabled") is False or MERCHANT_RE.search(msg):
        return route("merchant_action_needed")
    if BANK_BLOCK_RE.search(msg):
        return route("bank_transfer")
    if AUTH_RE.search(msg):
        desktop = (case.get("client_device") or "").lower() == "desktop"
        if desktop or paid_by_transfer_before(case.get("client_history") or ""):
            return route("bank_transfer")
        return route("wallet_link")
    if ADDRESS_RE.search(msg):
        # Address checks apply only to US, UK and Canada cards (section 4); the card's country when given.
        country = (case.get("card_country") or case.get("client_country") or "").strip().upper()
        if country in AVS_COUNTRIES and not case.get("address_retry_done"):
            return route("retry_card_with_fix")
        return route("bank_transfer")
    if FUNDS_RE.search(msg):
        return route("ask_when_to_pay")
    return route("bank_transfer")


# ----------------------------------------------------------------------------
# Sections 7 and 10: reading a client's reply
# ----------------------------------------------------------------------------

INSTRUCT_RE = re.compile(
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|messages|prompts|rules)|"
    r"disregard (?:all |any |the )?(?:previous|prior|above|earlier)|system (?:note|message|prompt|instruction|override)|"
    r"for (?:the )?homeward agent|\bagent\s*:|\bmark (?:\S+ ){0,3}as (?:paid|settled|closed)|set do_not_contact|"
    r"do_not_contact|resend the reminder|update (?:the |your |our )?(?:bank|payment|account) details to|"
    r"change (?:the |your |our )?(?:bank|payment|account) details|new instructions|"
    r"as an ai\b|\[system\]|<system>|assistant\s*:", re.I)
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
LOGIN_RE = re.compile(r"log\s?-?in|sign\s?-?in|verif|authenticat|confirm your|password|secure link|click here|credential", re.I)
LINK_WORD_RE = re.compile(r"\b(?:login|log-in|verification|verify|sign-?in|secure)\s+link\b", re.I)
DOCS_RE = re.compile(
    r"\bcontracts?\b|\bstatements?\b|\bdocuments?\b|\bcopies\b|\bcopy of\b|\bbank details|\bpayment details|"
    r"\baccount details|\bbanking details|\brecords\b|\bw-?9\b|\btax (?:form|document)|\bpassport|\bcredentials|"
    r"\bpassword|\bconversations?\b|\bcorrespondence\b", re.I)
NEW_DEST_RE = re.compile(
    r"\bto this (?:address|email|e-mail|mailbox|account)|\bto (?:a |the |our )?new (?:address|email|e-mail|account|contact|bank)|"
    r"\bto (?:our |the |my )?(?:auditor|accountant|lawyer|solicitor|consultant)|\bwith (?:our |the |my )?(?:auditor|accountant|lawyer|solicitor)|"
    r"\b(?:at|to)\s+[\w.+-]+@[\w.-]+|\bto the following|\bto the address below|\bchanged banks?\b|\bnew bank\b|"
    r"\bupdated bank\b|\bto this account\b|\bsend (?:\S+ ){0,4}here\b", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")


def is_suspicious(case, text):
    t = text or ""
    frm = (case.get("from") or "").strip().lower()
    known = (case.get("client_known_domain") or "").strip().lower()
    if frm and known:
        dom = frm.split("@")[-1]
        if dom != known and not dom.endswith("." + known):
            return True
    if INSTRUCT_RE.search(t):
        return True
    if LINK_WORD_RE.search(t):
        return True
    if URL_RE.search(t) and LOGIN_RE.search(t):
        return True
    if DOCS_RE.search(t) and NEW_DEST_RE.search(t):
        return True
    if known and DOCS_RE.search(t):
        for dom in EMAIL_RE.findall(t):
            dom = dom.lower()
            if dom != known and not dom.endswith("." + known):
                return True
    return False


OOO_RE = re.compile(
    r"out of (?:the )?office|\booo\b|away from (?:the|my) (?:office|desk)|\bon (?:annual |parental |maternity |paternity |sick )?leave\b|"
    r"on holiday|on vacation|travell?ing|will be back|\bbe back\b|\bback (?:in the office|at my desk|in office)\b|return(?:ing)? to the office|"
    r"auto.?reply|automatic reply|automated (?:response|reply|message)|automatische antwort|nicht im (?:büro|buero|haus)|"
    r"abwesend|au[ßs]er haus|fuera de la oficina|ausente|de vacaciones|\babsente?\b|en cong[ée]|en d[ée]placement|"
    r"hors du bureau|afwezig|niet (?:op kantoor|aanwezig)|met vakantie|buiten kantoor|limited access to (?:e-?mail|email)|"
    r"no access to (?:e-?mail|email)|keinen zugriff auf e-?mail", re.I)
STOP_RE = re.compile(
    r"\bremove (?:me|us)\b|unsubscribe|\bstop (?:emailing|e-mailing|contacting|sending|messaging|writing|chasing)|\bstop (?:these |the |all )?(?:emails|reminders|messages)|"
    r"\btake (?:me|us|this address|this email) off\b|off your (?:reminder |mailing |email |contact )?list|\bdo not contact\b|\bdon't contact\b|"
    r"\bno (?:more|further) (?:emails|e-mails|reminders|messages|contact)|\bleave (?:me|us) alone|\bcease\b|no longer wish to receive|"
    r"\bopt out\b|nicht mehr (?:kontaktieren|anschreiben|schreiben)|keine weiteren (?:e-?mails|erinnerungen|nachrichten)|"
    r"ne plus (?:nous|me) (?:contacter|écrire|relancer)|d[ée]sabonn|no (?:me|nos) (?:contacten|escriban|env[íi]en)|dar de baja|"
    r"niet meer (?:mailen|contacteren|benaderen)|afmelden", re.I)
WRONG_CONTACT_RE = re.compile(
    r"\bnew role\b|\bmoved (?:to|across|on|over)\b|\bno longer (?:work|handle|responsible|with|at|look|deal|manage|in charge)|"
    r"\bleft the (?:company|business|firm)\b|\bcontact (?:\S+ ){1,6}instead\b|\binstead\b.{0,40}@|"
    r"\b(?:handles?|looks? after|is responsible for|takes? care of|in charge of|manages?|deals? with|owns?|runs?) (?:the |our |all |supplier )?(?:payments|payables|invoices|accounts|ap\b|billing|finance)|"
    r"\bhanding over\b|\bhand(?:ed)? over\b|\btak(?:es?|ing) over\b|\bnow handles\b|\bcopied (?:her|him|them|\w+) in\b|"
    r"\bsend (?:future |all |any |the |your )?invoices to\b|\bforward (?:this |future |all )?(?:invoices|reminders) to\b|"
    r"\bright person\b|\bwrong person\b|\bnot the right contact\b|\bwrong contact\b|\bparental leave\b|\bmaternity leave\b|"
    r"\breach out to (?:\S+ ){1,4}instead|\bmy colleague\b|\bplease (?:use|email|write to|cc|copy) [\w.+-]+@|\bis now (?:your|the) contact\b|"
    r"\bnicht mehr zuständig|\bzuständig ist (?:jetzt|nun)|\bwenden sie sich (?:bitte )?an\b.{0,60}zuständig|\bya no (?:me ocupo|trabajo|soy)|"
    r"\bne (?:m'occupe|travaille) plus|\bwerk hier niet meer|\bniet meer verantwoordelijk", re.I)
PAID_WORD_RE = re.compile(r"\bpaid\b", re.I)
PAID_NEG_BEFORE_RE = re.compile(
    r"(?:\b(?:haven't|hasn't|hadn't|not|never|yet to|isn't|will be|be|get (?:this|it|that)|to be|didn't|won't be|wasn't|"
    r"are not|is not|have not|has not|can't be|cannot be|going to|about to|wird|werden|sera|seront|wordt|zal|zullen|"
    r"no hemos|no han|pas encore|noch nicht|nog niet)|n't)\s*$", re.I)
PAID_OTHER_AFTER_RE = re.compile(r"^\s*(?:the |an?)?(?:other|another|previous|last|earlier) invoice", re.I)
PAID_PHRASES_RE = re.compile(
    r"\bwire (?:left|went out|was sent|has been sent|has gone|is out)|\b(?:transfer|payment|funds|money|it|this) (?:left|went out|was sent|has been sent|was made|has been made|was released|has been released|has gone out|went through|has been processed|was processed)|"
    r"\bwent out by\b|\bsent (?:the|a|our|you the) (?:payment|wire|transfer|funds|money)\b|\bremittance\b|\bhas been settled|\bwas settled|\bwe settled (?:it|this|that)\b|"
    r"\bsettled (?:it|this|the invoice) (?:on|yesterday|last)|\btransferred (?:it|the|this|the amount)\b|\bmade the (?:payment|transfer)\b|"
    r"\bpayment (?:was|has been) (?:sent|made|released|processed|completed)|"
    # Spanish
    r"\brealizamos el pago|\bhemos pagado|\bya pagamos|\bya (?:hemos |lo |la )?(?:pagado|transferido|realizado|enviado)|\bpago realizado|\bpagamos (?:el|la) \w+ pasad[oa]|"
    # German
    r"\bbezahlt\b|\büberwiesen\b|\bueberwiesen\b|\bzahlung (?:ist|wurde) (?:erfolgt|angewiesen|ausgeführt|getätigt)|\bist raus\b|\bbereits (?:bezahlt|überwiesen|beglichen)|\bbeglichen\b|"
    # French
    r"\ba été (?:envoyé|effectué|réglé|payé|viré)|\bavons (?:payé|réglé|effectué|envoyé|viré)|\bvirement (?:a été|est) (?:envoyé|parti|effectué|fait)|\bdéjà (?:payé|réglé)|\bpayée?\b|\bréglée?\b|"
    # Dutch
    r"\bbetaald\b|\bovergemaakt\b|\bis verzonden\b|\bhebben (?:\S+ ){0,4}betaald|\bal betaald",
    re.I)
QUESTION_RE = re.compile(
    r"\bpo number|\bpurchase order|\bp\.?o\.?\s*(?:number|no\.?|#)|\bpo\s+\d|\bno po\b|\bsplit\b|\btwo halves\b|\bin halves\b|\bhalf now\b|\bpay half\b|"
    r"\binsta?llments?\?|\bduplicate|\bbilled twice|\bcharged twice|\bdouble.?(?:billed|charged)|\breissue|\bre-issue|\bbilling entity|"
    r"\bbreakdown\b|\bspecification\b|\bitemi[sz]ed|\bwhich invoices?\b|\bw-?9\b|\btax form|\bvat number|\bgst\b|"
    r"\bcan we pay (?:\S+ ){0,6}(?:in|over|later|instead)|\bis it ok if we pay|\bcould you (?:send|resend|re-send|reissue) (?:the|a|an|this|us a) (?:invoice|copy)|"
    r"\bcopy of the invoice|\binvoice copy|\bpayment terms\b|\bnet (?:30|45|60|90)\b|\bextend(?:ed)? (?:the )?(?:due date|terms)|"
    r"\bpay (?:\S+ ){0,3}in (?:two|three|\d) (?:parts|instalments|installments|payments|halves)|\bkunt u bevestigen|\bspezifikation|"
    r"\baufschlüsselung|\bbestellnummer|\bdesglose|\bnúmero de pedido|\bbon de commande|\bdétail de la facture|\bbestelnummer", re.I)
BANK_REQUEST_RE = re.compile(
    r"\bbank details|\bbanking details|\baccount details|\bbank account (?:details|number|info)|\biban\b|\bswift\b|\bbic\b|\brouting (?:number|details)|"
    r"\bsort code|\baccount number|\bwire (?:details|instructions|info)|\btransfer details|\bremittance details|\blocal (?:\w+ ){0,2}account\b|"
    r"\bbankgegevens|\bbankverbindung|\bkontodaten|\bkontonummer|\bcoordonnées bancaires|\brib\b|\bdatos bancarios|\bcuenta bancaria|\brekeningnummer", re.I)
BANK_PAY_RE = re.compile(
    r"\b(?:pay|paying|payment|settle|send it|send this|send the money|transfer it) (?:\S+ ){0,3}(?:by|via|through|per) (?:bank |wire |direct )?(?:transfer|wire|ach|sepa|eft|bacs|faster payments?)\b|"
    r"\bbank transfer\b|\bby wire\b|\bvia (?:sepa|ach|wire|transfer|bank)\b|\bper (?:überweisung|banküberweisung|sepa)|\bpar virement|\bpor transferencia|\bvia overboeking|\bover(?:maken|boeken)\b", re.I)
FAIL_RE = re.compile(
    r"\bdeclined?\b|\bstill failing|\bfailing\b|\bfailed\b|\bfails?\b|\berror\b|\bnot go(?:ing)? through|\bdidn't go through|\bwon't go through|\bdoesn't go through|"
    r"\btried again|\btry again|\btried (?:\S+ ){0,4}again|\bsame (?:red )?error|\brejected\b|\bblocked\b|\bkeeps (?:throwing|failing|rejecting|declining)|"
    r"\bcan't (?:get it to |seem to )?(?:pay|work)|\bwon't accept|\bnot accepted|\bcheckout (?:\S+ ){0,3}(?:eaten|broken|crash|dead)|\bbounced\b|"
    r"\babgelehnt|\bfehlgeschlagen|\bfunktioniert nicht|\brechazad|\bno funciona|\brefus[ée]|\béchou|\bne fonctionne pas|\bgeweigerd|\bmislukt|\bwerkt niet", re.I)


def says_paid(text):
    """A past-tense claim that this invoice has been paid, ignoring negated claims ("haven't paid yet",
    "will be paid") and claims about another invoice ("paid the other invoice")."""
    t = text or ""
    for rx in (PAID_WORD_RE, PAID_PHRASES_RE):
        for m in rx.finditer(t):
            before = t[max(0, m.start() - 24): m.start()]
            after = t[m.end(): m.end() + 30]
            if PAID_NEG_BEFORE_RE.search(before):
                continue
            if PAID_OTHER_AFTER_RE.search(after):
                continue
            return True
    return False


def reply_rule(case):
    cid = case["id"]
    text = strip_quotes(case.get("reply") or "")
    base = parse_base(case.get("reply_date"))

    def out(label, d=None):
        return {"id": cid, "label": label, "date": d.isoformat() if d else None}

    if is_suspicious(case, text):
        return out("suspicious")
    if is_dispute(text):
        return out("dispute")
    if OOO_RE.search(text):
        d = return_date(text, base)
        if d and d >= base:
            return out("out_of_office", d)
    if WRONG_CONTACT_RE.search(text):
        return out("wrong_contact")
    if STOP_RE.search(text):
        return out("stop_contact")
    if says_paid(text):
        return out("already_paid")
    if QUESTION_RE.search(text):
        return out("question_about_invoice")
    if BANK_REQUEST_RE.search(text):
        return out("asks_bank_details")
    d = pay_date(text, base)
    if d:
        return out("will_pay_on_date", d)
    if BANK_PAY_RE.search(text):
        return out("asks_bank_details")
    if FAIL_RE.search(text):
        return out("payment_failed_again")
    return out("no_action")


if __name__ == "__main__":
    for prefix in ("", "hard_", "safety_", "fresh_"):
        for name, fn in [("matching", match_rule), ("declines", decline_rule), ("replies", reply_rule)]:
            src = INP / "{}{}.json".format(prefix, name)
            if not src.exists():
                continue
            out = [fn(c) for c in json.loads(src.read_text())]
            (OUT / "fair_{}{}.json".format(prefix, name)).write_text(json.dumps(out, indent=1))
            print(prefix + name, len(out))
