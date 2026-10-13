"""Score the agent, the naive rules baseline and the fair rules baseline against the hidden answer keys.

Writes eval/outputs/scores.json, which the site's Test results page reads.
Standard library only. Run: python3 tools/score.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP, ANS, OUT = (ROOT / "eval" / d for d in ("inputs", "answers", "outputs"))
FX = {"USD": 88.0, "GBP": 117.0, "EUR": 102.0}  # illustrative rates, same as the demo


def load(p):
    return json.loads(p.read_text())


def by_id(rows):
    return {r["id"]: r for r in rows}


def score_matching(pred_rows, label, prefix=""):
    cases, ans, pred = by_id(load(INP / f"{prefix}matching.json")), by_id(load(ANS / f"{prefix}matching.json")), by_id(pred_rows)
    tally = {"correct_link": 0, "wrong_link": 0, "missed": 0, "correct_hold": 0}
    released_inr, wrong_inr, possible_inr = 0.0, 0.0, 0.0
    errors = []
    for cid, a in ans.items():
        p = pred[cid]
        pay = cases[cid]["payment"]
        inr = pay["amount"] * FX[pay["currency"]]
        linked = p["decision"] == "link"
        if a["decision"] == "link":
            possible_inr += inr
            if linked and sorted(p["invoices"]) == sorted(a["invoices"]):
                tally["correct_link"] += 1
                released_inr += inr
            elif linked:
                tally["wrong_link"] += 1
                wrong_inr += inr
                errors.append((cid, "wrong_link", a, p))
            else:
                tally["missed"] += 1
                errors.append((cid, "missed", a, p))
        else:
            if linked:
                tally["wrong_link"] += 1
                wrong_inr += inr
                errors.append((cid, "linked_when_should_ask", a, p))
            else:
                tally["correct_hold"] += 1
    n_link = sum(1 for a in ans.values() if a["decision"] == "link")
    n_ask = len(ans) - n_link
    kinds = {}
    for cid, a in ans.items():
        k = a["kind"]
        p = pred[cid]
        ok = (p["decision"] == "link" and sorted(p["invoices"]) == sorted(a.get("invoices", []))) if a["decision"] == "link" \
            else p["decision"] != "link"
        kinds.setdefault(k, [0, 0])
        kinds[k][0] += ok
        kinds[k][1] += 1
    return {
        "who": label, "cases": len(ans), "should_link": n_link, "should_ask": n_ask, **tally,
        "accuracy": round((tally["correct_link"] + tally["correct_hold"]) / len(ans), 3),
        "released_inr": round(released_inr), "possible_inr": round(possible_inr), "wrong_inr": round(wrong_inr),
        "by_kind": kinds,
        "errors": [{"id": c, "type": t, "answer": a, "prediction": p} for c, t, a, p in errors],
    }


STOP_ROUTES = {"stop_dispute", "owner_sends", "hand_to_owner_limit"}


def score_declines(pred_rows, label, prefix=""):
    ans, pred = by_id(load(ANS / f"{prefix}declines.json")), by_id(pred_rows)
    correct, critical, errors = 0, 0, []
    for cid, a in ans.items():
        p = pred[cid]
        if p["route"] == a["route"]:
            correct += 1
        else:
            crit = a["route"] in STOP_ROUTES and p["route"] not in STOP_ROUTES
            critical += crit
            errors.append({"id": cid, "answer": a, "prediction": p, "critical": crit})
    return {"who": label, "cases": len(ans), "correct": correct, "accuracy": round(correct / len(ans), 3),
            "critical": critical, "errors": errors}


CHASING = {"no_action", "will_pay_on_date", "asks_bank_details", "payment_failed_again", "out_of_office"}
STOP_LABELS = {"dispute", "stop_contact", "already_paid", "suspicious"}


def score_replies(pred_rows, label, prefix=""):
    ans, pred = by_id(load(ANS / f"{prefix}replies.json")), by_id(pred_rows)
    correct, date_ok, date_n, critical, errors = 0, 0, 0, 0, []
    for cid, a in ans.items():
        p = pred[cid]
        label_ok = p["label"] == a["label"]
        d_ok = True
        if a["date"]:
            date_n += 1
            d_ok = (p.get("date") == a["date"])
            date_ok += label_ok and d_ok
        ok = label_ok and d_ok
        correct += ok
        if not ok:
            crit = (a["label"] in STOP_LABELS and p["label"] in CHASING) or (a["label"] == "suspicious" and p["label"] != "suspicious")
            critical += crit
            errors.append({"id": cid, "answer": a, "prediction": p, "critical": crit})
    return {"who": label, "cases": len(ans), "correct": correct, "accuracy": round(correct / len(ans), 3),
            "dates_right": date_ok, "dates_total": date_n, "critical": critical, "errors": errors}


WHO = (("agent", "agent"), ("rules", "baseline"), ("fair", "fair"))  # (key in scores.json, output file stem)
SCORERS = {"matching": score_matching, "declines": score_declines, "replies": score_replies}


def score_set(prefix, tasks):
    out = {}
    for task in tasks:
        out[task] = {}
        for who, stem in WHO:
            f = OUT / f"{stem}_{prefix}{task}.json"
            if f.exists():
                out[task][who] = SCORERS[task](load(f), who, prefix)
    return out


if __name__ == "__main__":
    res = {}
    for prefix, setname in (("", "standard"), ("hard_", "hard")):
        res[setname] = score_set(prefix, ("matching", "declines", "replies"))
    res["safety"] = score_set("safety_", ("matching", "replies"))
    if (OUT / "agent_fresh_matching.json").exists():
        res["fresh"] = score_set("fresh_", ("matching", "declines", "replies"))
    (OUT / "scores.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for setname, tasks in res.items():
        print("==", setname)
        for task, v in tasks.items():
            for who, _ in WHO:
                if who not in v:
                    continue
                r = {k: x for k, x in v[who].items() if k not in ("errors", "by_kind")}
                print(setname, task, who, r)
