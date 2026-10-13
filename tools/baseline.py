"""The rules baseline: what a fixed rule set does on the same blind test inputs.

Matching: link only on an exact invoice number in the reference with the exact amount,
or an exact client name with exactly one open invoice of the exact amount. Otherwise leave unmatched.
Declines: keyword rules on the decline message only.
Replies: keyword rules on the reply text.

Standard library only. Run: python3 tools/baseline.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / "eval" / "inputs"
OUT = ROOT / "eval" / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def match_rule(case):
    p = case["payment"]
    opens = [i for i in case["open_and_recent_invoices"] if i["status"] == "open"]
    ref = norm(p["reference"])
    by_ref = [i for i in opens if norm(i["invoice"]) in ref]
    if len(by_ref) == 1:
        i = by_ref[0]
        if i["currency"] == p["currency"] and abs(i["amount"] - p["amount"]) < 0.005:
            return {"id": case["id"], "decision": "link", "invoices": [i["invoice"]], "reason": "Exact invoice number and amount"}
    payer = norm(p["payer_name"])
    same_name = [i for i in opens if norm(i["client"]) == payer and i["currency"] == p["currency"]
                 and abs(i["amount"] - p["amount"]) < 0.005]
    if len(same_name) == 1:
        return {"id": case["id"], "decision": "link", "invoices": [same_name[0]["invoice"]], "reason": "Exact client name and amount"}
    return {"id": case["id"], "decision": "unmatched", "invoices": [], "reason": "No exact rule fired"}


def decline_rule(case):
    m = case["decline_message"].lower()
    if "3-d secure" in m or "3ds" in m or "authentication" in m:
        r = "wallet_link"
    elif "avs" in m or "address" in m:
        r = "retry_card_with_fix"
    elif "insufficient" in m or "limit" in m:
        r = "ask_when_to_pay"
    elif "merchant" in m:
        r = "merchant_action_needed"
    else:
        r = "bank_transfer"
    return {"id": case["id"], "route": r}


WEEKDAYS = {"monday": "2026-10-12", "tuesday": "2026-10-13", "wednesday": "2026-10-14",
            "thursday": "2026-10-15", "friday": "2026-10-16"}
MONTHS = {"october": "10", "november": "11"}


def find_date(t):
    m = re.search(r"(\d{1,2})\s+(october|november)", t)
    if m:
        return f"2026-{MONTHS[m.group(2)]}-{int(m.group(1)):02d}"
    m = re.search(r"the (\d{1,2})(st|nd|rd|th)", t)
    if m:
        return f"2026-10-{int(m.group(1)):02d}"
    for w, d in WEEKDAYS.items():
        if w in t:
            return d
    return None


def reply_rule(case):
    t = case["reply"].lower()
    date = None
    if "dispute" in t:
        label = "dispute"
    elif "paid" in t:
        label = "already_paid"
    elif "out of office" in t:
        label, date = "out_of_office", find_date(t)
    elif "bank details" in t or "bank transfer" in t or "wire" in t:
        label = "asks_bank_details"
    elif "stop" in t or "remove me" in t or "unsubscribe" in t:
        label = "stop_contact"
    elif "declined" in t or "failing" in t or "error" in t:
        label = "payment_failed_again"
    elif "contact" in t or "new role" in t:
        label = "wrong_contact"
    elif find_date(t):
        label, date = "will_pay_on_date", find_date(t)
    else:
        label = "no_action"
    return {"id": case["id"], "label": label, "date": date}


if __name__ == "__main__":
    for prefix in ("", "hard_", "safety_", "fresh_"):
        for name, fn in [("matching", match_rule), ("declines", decline_rule), ("replies", reply_rule)]:
            src = INP / f"{prefix}{name}.json"
            if not src.exists():
                continue
            out = [fn(c) for c in json.loads(src.read_text())]
            (OUT / f"baseline_{prefix}{name}.json").write_text(json.dumps(out, indent=1))
            print(prefix + name, len(out))
