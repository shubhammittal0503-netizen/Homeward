"""Generate the blind test sets for Homeward.

Three sets, each with inputs (what the agent sees) and answer keys (hidden from the agent):
  matching  60 payments to link to invoices or hand to the owner
  declines  30 declined card payments needing the next way to pay
  replies   30 client replies to classify

Standard library only. Seeded, so the sets are reproducible.
Run: python3 tools/make_tests.py
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / "eval" / "inputs"
ANS = ROOT / "eval" / "answers"
INP.mkdir(parents=True, exist_ok=True)
ANS.mkdir(parents=True, exist_ok=True)

rng = random.Random(20261012)

# Fictional clients. Variants are how their name can appear as the payer on a bank transfer.
CLIENTS = [
    {"name": "Larkspur Labs Inc", "country": "US", "ccy": "USD", "domain": "larkspurlabs.example",
     "variants": ["LARKSPUR LABS INC", "LARKSPUR LABS"], "parent": "LARKSPUR HOLDINGS LLC"},
    {"name": "Bramble & Finch Ltd", "country": "GB", "ccy": "GBP", "domain": "brambleandfinch.example",
     "variants": ["BRAMBLE AND FINCH LIMITED", "BRAMBLE & FINCH"], "parent": "BRAMBLE FINCH GROUP PLC"},
    {"name": "Kestrel Analytics GmbH", "country": "DE", "ccy": "EUR", "domain": "kestrel-analytics.example",
     "variants": ["KESTREL ANALYTICS GMBH", "KESTREL ANALYTICS"], "parent": "KESTREL HOLDING AG"},
    {"name": "Tidewater Health LLC", "country": "US", "ccy": "USD", "domain": "tidewaterhealth.example",
     "variants": ["TIDEWATER HEALTH LLC", "TIDEWATER HLTH LLC"], "parent": "TIDEWATER CARE PARTNERS INC"},
    {"name": "Copperline Studios Pty Ltd", "country": "AU", "ccy": "USD", "domain": "copperline.example",
     "variants": ["COPPERLINE STUDIOS PTY LTD", "COPPERLINE STUDIOS"], "parent": "COPPERLINE GROUP PTY LTD"},
    {"name": "Halcyon Retail Pte Ltd", "country": "SG", "ccy": "USD", "domain": "halcyonretail.example",
     "variants": ["HALCYON RETAIL PTE. LTD.", "HALCYON RETAIL"], "parent": "HALCYON GROUP HOLDINGS PTE LTD"},
    {"name": "Saltmarsh Media Ltd", "country": "GB", "ccy": "GBP", "domain": "saltmarshmedia.example",
     "variants": ["SALTMARSH MEDIA LIMITED", "SALTMARSH MEDIA"], "parent": "SALTMARSH PUBLISHING GROUP LTD"},
    {"name": "Juniper Ridge Inc", "country": "CA", "ccy": "USD", "domain": "juniperridge.example",
     "variants": ["JUNIPER RIDGE INC", "JUNIPER RIDGE"], "parent": "JUNIPER RIDGE HOLDINGS CORP"},
    {"name": "Fernhill Analytics Ltd", "country": "GB", "ccy": "GBP", "domain": "fernhill.example",
     "variants": ["FERNHILL ANALYTICS LIMITED", "FERNHILL ANALYTICS"], "parent": "FERNHILL DATA GROUP LTD"},
    {"name": "Orchard Lane Software Inc", "country": "US", "ccy": "USD", "domain": "orchardlane.example",
     "variants": ["ORCHARD LANE SOFTWARE INC", "ORCHARD LANE SOFTWARE"], "parent": "ORCHARD LANE HOLDINGS INC"},
    {"name": "Bluefin Mobility BV", "country": "NL", "ccy": "EUR", "domain": "bluefin-mobility.example",
     "variants": ["BLUEFIN MOBILITY B.V.", "BLUEFIN MOBILITY"], "parent": "BLUEFIN GROEP B.V."},
    {"name": "Marigold Learning Inc", "country": "US", "ccy": "USD", "domain": "marigoldlearning.example",
     "variants": ["MARIGOLD LEARNING INC", "MARIGOLD LEARNING"], "parent": "MARIGOLD EDUCATION GROUP LLC"},
    {"name": "Pinecrest Advisory LLP", "country": "GB", "ccy": "GBP", "domain": "pinecrestadvisory.example",
     "variants": ["PINECREST ADVISORY LLP", "PINECREST ADVISORY"], "parent": "PINECREST PARTNERS LTD"},
    {"name": "Wren & Oak GmbH", "country": "DE", "ccy": "EUR", "domain": "wrenandoak.example",
     "variants": ["WREN AND OAK GMBH", "WREN & OAK"], "parent": "WREN OAK HOLDING GMBH"},
    {"name": "Silverbirch Labs Ltd", "country": "IE", "ccy": "EUR", "domain": "silverbirch.example",
     "variants": ["SILVERBIRCH LABS LIMITED", "SILVERBIRCH LABS"], "parent": "SILVERBIRCH VENTURES DAC"},
    {"name": "Northbeam Retail Inc", "country": "US", "ccy": "USD", "domain": "northbeam.example",
     "variants": ["NORTHBEAM RETAIL INC", "NORTHBEAM RETAIL"], "parent": "NORTHBEAM BRANDS LLC"},
]
UNKNOWN_PAYERS = ["QUILLON DESIGNWORKS", "MERIDIAN FORGE LTD", "ASHGROVE TRADING CO", "VELLUM & STONE LLC",
                  "HARBOURLIGHT VENTURES", "CINDERFALL MEDIA SL"]
RAIL = {"USD": "ACH", "GBP": "Faster Payments", "EUR": "SEPA"}
FEE = {"USD": (12, 45), "GBP": (8, 30), "EUR": (10, 35)}

used_numbers = set()


def new_number():
    while True:
        n = rng.randint(1101, 1499)
        if n not in used_numbers:
            used_numbers.add(n)
            return f"SL-{n}"


def amount(ccy):
    base = rng.choice([450, 600, 750, 800, 950, 1200, 1250, 1500, 1800, 2000, 2250, 2400, 2750, 3000, 3200, 3600, 4100, 4800])
    if rng.random() < 0.25:
        base += rng.choice([25, 50, 75, 125.5, 62.5])
    return round(float(base), 2)


def invoice_date():
    """Invoices are dated between 1 Aug and 5 Oct 2026, before any payment in the sets arrives."""
    month = rng.choice(["08", "09", "09", "10"])
    day = rng.randint(1, 5) if month == "10" else rng.randint(1, 28)
    return f"2026-{month}-{day:02d}"


def inv(client, amt=None, status="open", day=None):
    return {
        "invoice": new_number(),
        "client": client["name"],
        "client_country": client["country"],
        "currency": client["ccy"],
        "amount": amt if amt is not None else amount(client["ccy"]),
        "date": invoice_date(),
        "status": status,
    }


def others(exclude, k):
    pool = [c for c in CLIENTS if c["name"] != exclude["name"]]
    return rng.sample(pool, k)


def distractors(client, true_amounts, n_same_client=1, n_other=2, same_amount_other=None, ccy=None):
    out = []
    for _ in range(n_same_client):
        a = amount(client["ccy"])
        while a in true_amounts:
            a = amount(client["ccy"])
        out.append(inv(client, a))
    for o in others(client, n_other):
        out.append(inv(o))
    if same_amount_other is not None:
        o = others(client, 1)[0]
        # same amount and currency as the payment but a different client: a trap for amount-only matching
        d = inv(o, same_amount_other)
        d["currency"] = ccy or client["ccy"]
        out.append(d)
    return out


def num_only(invno):
    return invno.replace("SL-", "")


def typo(invno):
    n = num_only(invno)
    options = [
        f"SL-{n.replace('0', 'O', 1)}" if "0" in n else f"SL {n}",
        f"INV {n}",
        f"#{n} {rng.choice(['sprint', 'design', 'Oct', 'milestone'])}",
        f"SL{n} PAYMENT",
        f"sl - {n}",
        f"Invoice no. {n}",
    ]
    return rng.choice(options)


def payment(payer, ccy, amt, ref, day=None):
    return {
        "rail": RAIL[ccy] if rng.random() < 0.8 else "SWIFT",
        "currency": ccy,
        "amount": round(amt, 2),
        "payer_name": payer,
        "reference": ref,
        "received": f"2026-10-{day or rng.randint(6, 11):02d}",
    }


matching_inputs, matching_answers = [], []


def add_match(kind, pay, invoices, aliases, answer):
    invoices = invoices[:]
    rng.shuffle(invoices)
    matching_inputs.append({"payment": pay, "open_and_recent_invoices": invoices, "known_payer_aliases": aliases})
    matching_answers.append({"kind": kind, **answer})


# 1. Exact: payer is the client, reference has the invoice number, amount equal (7)
for _ in range(7):
    c = rng.choice(CLIENTS)
    t = inv(c)
    ref = rng.choice([t["invoice"], f"Invoice {t['invoice']}", f"{t['invoice']} {rng.choice(['design', 'sprint 2', 'Oct'])}"])
    add_match("exact", payment(c["variants"][0], c["ccy"], t["amount"], ref),
              [t] + distractors(c, [t["amount"]]), {}, {"decision": "link", "invoices": [t["invoice"]], "amount": t["amount"]})

# 2. Alias payer: parent company or payment service (7); 4 with the alias known, 3 evident from the reference
for i in range(7):
    c = rng.choice(CLIENTS)
    t = inv(c)
    if i < 4:
        payer = c["parent"]
        aliases = {c["name"]: [c["parent"]]}
        ref = rng.choice([t["invoice"], num_only(t["invoice"]), f"{c['name'].split()[0]} payment"])
        if ref == f"{c['name'].split()[0]} payment":
            ref = f"{t['invoice']}"
    else:
        if rng.random() < 0.5:
            payer = rng.choice(["WISE US INC", "WISE PAYMENTS LTD", "WISE EUROPE SA"])
            ref = f"{c['name'].upper()} {t['invoice']}"
        else:
            payer = c["parent"]
            ref = f"{t['invoice']} {c['name'].split()[0].upper()}"
        aliases = {}
    add_match("alias", payment(payer, c["ccy"], t["amount"], ref),
              [t] + distractors(c, [t["amount"]], same_amount_other=t["amount"]), aliases,
              {"decision": "link", "invoices": [t["invoice"]], "amount": t["amount"]})

# 3. Short by a typical bank charge (8)
for _ in range(8):
    c = rng.choice(CLIENTS)
    t = inv(c)
    lo, hi = FEE[c["ccy"]]
    fee = rng.randint(lo, hi)
    while fee > 0.03 * t["amount"]:
        t["amount"] = round(t["amount"] + 500, 2)
    ref = rng.choice([num_only(t["invoice"]), t["invoice"], f"{t['invoice']} less charges", f"INV{num_only(t['invoice'])}"])
    payer = rng.choice(c["variants"] + [c["parent"]])
    aliases = {c["name"]: [c["parent"]]} if payer == c["parent"] else {}
    add_match("short", payment(payer, c["ccy"], t["amount"] - fee, ref),
              [t] + distractors(c, [t["amount"]]), aliases,
              {"decision": "link", "invoices": [t["invoice"]], "amount": round(t["amount"] - fee, 2)})

# 4. Reference typos (6)
for _ in range(6):
    c = rng.choice(CLIENTS)
    t = inv(c)
    add_match("typo", payment(rng.choice(c["variants"]), c["ccy"], t["amount"], typo(t["invoice"])),
              [t] + distractors(c, [t["amount"]]), {},
              {"decision": "link", "invoices": [t["invoice"]], "amount": t["amount"]})

# 5. One transfer for two invoices of the same client (6)
for _ in range(6):
    c = rng.choice(CLIENTS)
    a, b = inv(c), inv(c)
    while b["amount"] == a["amount"]:
        b["amount"] = amount(c["ccy"])
    ref = rng.choice([f"{a['invoice']} + {b['invoice']}", f"{num_only(a['invoice'])}/{num_only(b['invoice'])}",
                      "October invoices", f"INV {num_only(a['invoice'])} {num_only(b['invoice'])}"])
    total = round(a["amount"] + b["amount"], 2)
    add_match("multi", payment(rng.choice(c["variants"]), c["ccy"], total, ref),
              [a, b] + distractors(c, [a["amount"], b["amount"], total], n_same_client=1, n_other=2), {},
              {"decision": "link", "invoices": sorted([a["invoice"], b["invoice"]]), "amount": total})

# 6. Stated part payment (4)
for _ in range(4):
    c = rng.choice(CLIENTS)
    t = inv(c)
    share = rng.choice([0.5, 0.4, 0.3])
    ref = rng.choice([f"Part payment {t['invoice']}", f"{int(share*100)}% advance {t['invoice']}",
                      f"{t['invoice']} instalment 1", f"Partial {num_only(t['invoice'])}"])
    add_match("part", payment(rng.choice(c["variants"]), c["ccy"], t["amount"] * share, ref),
              [t] + distractors(c, [t["amount"]]), {},
              {"decision": "link", "invoices": [t["invoice"]], "amount": round(t["amount"] * share, 2)})

# 7. No reference, a single fitting invoice of that client (6): 3 with the exact legal name, 3 with a variant
for i in range(6):
    c = rng.choice(CLIENTS)
    t = inv(c)
    payer = c["name"].upper() if i < 3 else c["variants"][1]
    add_match("noref_single", payment(payer, c["ccy"], t["amount"], rng.choice(["", "Payment", "Thank you", "Services"])),
              [t] + distractors(c, [t["amount"]], same_amount_other=t["amount"]), {},
              {"decision": "link", "invoices": [t["invoice"]], "amount": t["amount"]})

# 8. Ambiguous: two open invoices of the same client with the same amount, no useful reference (6)
for _ in range(6):
    c = rng.choice(CLIENTS)
    a = inv(c)
    b = inv(c, a["amount"])
    add_match("ambiguous", payment(rng.choice(c["variants"]), c["ccy"], a["amount"], rng.choice(["", "Payment", "Invoice payment", "October"])),
              [a, b] + distractors(c, [a["amount"]], n_same_client=0, n_other=2), {},
              {"decision": "ask", "reason_code": "ambiguous", "candidates": sorted([a["invoice"], b["invoice"]])})

# 9. Unknown payer (4): amount may equal another client's invoice
for _ in range(4):
    c = rng.choice(CLIENTS)
    t = inv(c)
    payer = rng.choice(UNKNOWN_PAYERS)
    UNKNOWN_PAYERS.remove(payer)
    add_match("unknown", payment(payer, c["ccy"], t["amount"], rng.choice(["Logo refresh", "Consulting", "Services Oct", ""])),
              [t] + distractors(c, [t["amount"]]), {},
              {"decision": "ask", "reason_code": "unknown_payer"})

# 10. Possible duplicate: the only matching invoice is already paid (4)
for _ in range(4):
    c = rng.choice(CLIENTS)
    t = inv(c, status="paid")
    add_match("duplicate", payment(rng.choice(c["variants"]), c["ccy"], t["amount"], rng.choice([t["invoice"], num_only(t["invoice"])])),
              [t] + distractors(c, [t["amount"]]), {},
              {"decision": "ask", "reason_code": "duplicate", "candidates": [t["invoice"]]})

# 11. Shortfall far beyond a bank charge, no part payment stated (2)
for _ in range(2):
    c = rng.choice(CLIENTS)
    t = inv(c)
    paid = round(t["amount"] * rng.choice([0.85, 0.8]), 2)
    add_match("large_short", payment(rng.choice(c["variants"]), c["ccy"], paid, t["invoice"]),
              [t] + distractors(c, [t["amount"]]), {},
              {"decision": "ask", "reason_code": "unexplained_shortfall", "candidates": [t["invoice"]]})

# Shuffle and assign neutral ids
order = list(range(len(matching_inputs)))
rng.shuffle(order)
mi, ma = [], []
for k, idx in enumerate(order, 1):
    cid = f"M{k:02d}"
    mi.append({"id": cid, **matching_inputs[idx]})
    ma.append({"id": cid, **matching_answers[idx]})

# Declines
DECLINE_TEXT = {
    "issuer_block": ["Do not honour (05)", "Declined by issuer: transaction not permitted to cardholder",
                     "Issuer declined. Cross-border risk rules", "Generic decline from issuing bank (code 05)",
                     "Your card issuer declined this international charge"],
    "fraud_suspected": ["Suspected fraud (59)", "Issuer flagged the payment as possible fraud"],
    "intl_blocked": ["Card not enabled for international e-commerce", "Transaction not allowed: card restricted to domestic use"],
    "blocked_after_attempts": ["Card blocked by issuer after repeated attempts", "Exceeds PIN or attempt limit; card temporarily locked by bank"],
    "auth_failed": ["3-D Secure authentication failed", "Cardholder did not complete the bank's verification step",
                    "Authentication not available: card not enrolled for secure verification",
                    "Payer closed the one-time password page before finishing"],
    "avs_mismatch": ["AVS mismatch: billing postcode does not match", "Address verification failed (N)",
                     "Billing address on file with the bank didn't match"],
    "insufficient": ["Insufficient funds (51)", "Exceeds withdrawal amount limit (61)"],
    "merchant_not_enabled": ["International cards are not enabled for this merchant account",
                             "Merchant account cannot accept cards issued outside India"],
}
HISTORY = {
    "bank": ["Paid two earlier invoices by bank transfer", "Usually pays by wire", "Paid the last invoice by ACH"],
    "card": ["Paid the last three invoices by card", "Always pays by card", "First invoice from this client"],
}


def route_truth(d):
    """The policy (section 6) applied to the structured facts."""
    if d["_reply_kind"] == "dispute":
        return "stop_dispute"
    if d["do_not_contact"]:
        return "owner_sends"
    if d["reminders_sent"] >= 2:
        return "hand_to_owner_limit"
    if d["_reply_kind"] == "date":
        return "wait_until_date"
    if not d["merchant_international_cards_enabled"]:
        return "merchant_action_needed"
    cat = d["_cat"]
    if cat in ("issuer_block", "fraud_suspected", "intl_blocked", "blocked_after_attempts"):
        return "bank_transfer"
    if cat == "auth_failed":
        if d["client_device"] == "desktop" or d["_hist"] == "bank":
            return "bank_transfer"
        return "wallet_link"
    if cat == "avs_mismatch":
        return "bank_transfer" if d["address_retry_done"] else "retry_card_with_fix"
    if cat == "insufficient":
        return "ask_when_to_pay"
    raise ValueError(cat)


plan = (
    [("issuer_block", {})] * 5 + [("fraud_suspected", {})] * 2 + [("intl_blocked", {})] * 2 +
    [("blocked_after_attempts", {})] * 2 +
    [("auth_failed", {"device": "mobile", "hist": "card"})] * 3 +
    [("auth_failed", {"device": "desktop", "hist": "card"}), ("auth_failed", {"device": "mobile", "hist": "bank"}),
     ("auth_failed", {"device": "unknown", "hist": "bank"})] +
    [("avs_mismatch", {"retry": False})] * 2 + [("avs_mismatch", {"retry": True})] +
    [("insufficient", {})] * 2 + [("merchant_not_enabled", {})] * 2 +
    [("auth_failed", {"reply": "dispute", "device": "mobile", "hist": "card"}), ("issuer_block", {"reply": "dispute"})] +
    [("issuer_block", {"dnc": True})] + [("avs_mismatch", {"reminders": 2})] +
    [("auth_failed", {"reply": "date", "device": "mobile", "hist": "card"}), ("insufficient", {"reply": "date"})]
)
DISPUTE_REPLIES = ["We don't agree with the hours billed for week 3. Please hold until we've talked.",
                   "This invoice doesn't match the quote we signed, so we won't be paying it as it stands."]
DATE_REPLIES = [("We'll pay by bank transfer on Friday 16 October.", "2026-10-16"),
                ("Our card limit resets on the 20th, I'll pay then.", "2026-10-20")]
NEUTRAL_REPLIES = [None, None, None, "Thanks, will look into it.", "Noted."]

declines_in, declines_ans = [], []
for cat, opts in plan:
    c = rng.choice([x for x in CLIENTS if x["country"] in ("US", "GB", "CA")]) if cat == "avs_mismatch" else rng.choice(CLIENTS)
    hist_key = opts.get("hist") or rng.choice(["bank", "card"])
    if cat in ("issuer_block", "fraud_suspected", "intl_blocked", "blocked_after_attempts", "insufficient", "merchant_not_enabled", "avs_mismatch"):
        hist_key = opts.get("hist") or rng.choice(["card", "card", "bank"])
    reply_kind = opts.get("reply")
    reply = None
    date = None
    if reply_kind == "dispute":
        reply = DISPUTE_REPLIES.pop(0)
    elif reply_kind == "date":
        reply, date = DATE_REPLIES.pop(0)
    else:
        reply = rng.choice(NEUTRAL_REPLIES)
    country = c["country"]
    d = {
        "decline_message": rng.choice(DECLINE_TEXT[cat]),
        "client": c["name"],
        "client_country": country,
        "currency": c["ccy"],
        "amount": amount(c["ccy"]),
        "client_history": rng.choice(HISTORY[hist_key]),
        "client_device": opts.get("device") or rng.choice(["mobile", "desktop", "unknown"]),
        "attempts": rng.randint(1, 3) if cat != "blocked_after_attempts" else rng.randint(3, 5),
        "reminders_sent": opts.get("reminders", rng.choice([0, 0, 1])),
        "address_retry_done": opts.get("retry", False),
        "client_reply": reply,
        "reply_date": "2026-10-09" if reply else None,
        "do_not_contact": opts.get("dnc", False),
        "merchant_international_cards_enabled": cat != "merchant_not_enabled",
        "_cat": cat, "_hist": hist_key, "_reply_kind": reply_kind,
    }
    if cat == "auth_failed" and "device" not in opts:
        d["client_device"] = "mobile"
    truth = route_truth(d)
    declines_ans.append({"route": truth, "category": cat, "date": date})
    declines_in.append({k: v for k, v in d.items() if not k.startswith("_")})

order = list(range(len(declines_in)))
rng.shuffle(order)
di, da = [], []
for k, idx in enumerate(order, 1):
    cid = f"D{k:02d}"
    di.append({"id": cid, **declines_in[idx]})
    da.append({"id": cid, **declines_ans[idx]})

# Replies: written by hand to include the traps a keyword rule falls into
REPLIES = [
    ("We paid this on Friday by wire, ref SL1061.", "already_paid", None),
    ("Haven't paid yet, it's going out Tuesday.", "will_pay_on_date", "2026-10-13"),
    ("Our AP team confirms the wire left on 2 October.", "already_paid", None),
    ("We're not paying until the week 3 hours are corrected.", "dispute", None),
    ("Not disputing anything, we just need a PO number on the invoice before we can pay.", "question_about_invoice", None),
    ("Please stop emailing me about this.", "stop_contact", None),
    ("I've moved to a new role. Please send invoices to ap@larkspurlabs.example from now on.", "wrong_contact", None),
    ("I am out of the office until 19 October with limited access to email.", "out_of_office", "2026-10-19"),
    ("Ich bin bis zum 16. Oktober nicht im Büro und habe keinen Zugriff auf E-Mails.", "out_of_office", "2026-10-16"),
    ("Could you send your bank details? Our finance team only pays by wire.", "asks_bank_details", None),
    ("Tried again with Apple Pay just now, still failing.", "payment_failed_again", None),
    ("Thanks for the reminder!", "no_action", None),
    ("Paid the other invoice yesterday; this one goes out with our 1 November payment run.", "will_pay_on_date", "2026-11-01"),
    ("We dispute nothing. Payment is scheduled for the 15th.", "will_pay_on_date", "2026-10-15"),
    ("Card got declined again. Our bank says they blocked it for security.", "payment_failed_again", None),
    ("Ya realizamos el pago por transferencia el viernes pasado.", "already_paid", None),
    ("Remove me from this list.", "stop_contact", None),
    ("Can we pay half now and the rest next month?", "question_about_invoice", None),
    ("Company policy: we only pay suppliers by bank transfer to a local US account. Please share one.", "asks_bank_details", None),
    ("Payment is approved and will be released on Thursday.", "will_pay_on_date", "2026-10-15"),
    ("The amount is wrong. We agreed USD 2,000, not 2,400.", "dispute", None),
    ("I'm on parental leave. Please contact Sam Ortiz (sam.ortiz@tidewaterhealth.example) instead.", "wrong_contact", None),
    ("Auto-reply: we have received your email and will respond within 3 business days.", "no_action", None),
    ("Already paid, remittance advice attached.", "already_paid", None),
    ("Is this a duplicate of SL-1058? We think we've been billed twice for the same sprint.", "question_about_invoice", None),
    ("We'll settle it on Monday, sorry for the delay.", "will_pay_on_date", "2026-10-12"),
    ("Out of office: back Wednesday 14 October. For urgent matters call reception.", "out_of_office", "2026-10-14"),
    ("Your page keeps throwing an error when I enter my card.", "payment_failed_again", None),
    ("We have not received the work for milestone 2, so we won't pay this yet.", "dispute", None),
    ("Got it, thanks. Passing to finance.", "no_action", None),
]
order = list(range(len(REPLIES)))
rng.shuffle(order)
ri, ra = [], []
for k, idx in enumerate(order, 1):
    text, label, date = REPLIES[idx]
    cid = f"R{k:02d}"
    ri.append({"id": cid, "context": "Reminder 1 sent after a declined card payment for an open invoice",
               "reply": text, "reply_date": "2026-10-09 (Friday)"})
    ra.append({"id": cid, "label": label, "date": date})

for name, data in [("matching", mi), ("declines", di), ("replies", ri)]:
    (INP / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
for name, data in [("matching", ma), ("declines", da), ("replies", ra)]:
    (ANS / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))

print(f"matching {len(mi)}, declines {len(di)}, replies {len(ri)}")
from collections import Counter
print("matching kinds", Counter(a["kind"] for a in ma))
print("decline routes", Counter(a["route"] for a in da))
print("reply labels", Counter(a["label"] for a in ra))
