"""Render the Homeward prototype as plain static HTML in docs/ (served by GitHub Pages).

Every word is in the HTML itself, so the pages read the same with or without JavaScript.
Inputs: tools/config.json, data/demo.json, eval/outputs/scores.json, eval/inputs/*.json, eval/outputs/agent_*.json.
Standard library only. Python 3.9 or later. Run: python3 tools/build_site.py
"""
import csv
import html
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CFG = json.loads((ROOT / "tools" / "config.json").read_text())
D = json.loads((ROOT / "data" / "demo.json").read_text())
S = json.loads((ROOT / "eval" / "outputs" / "scores.json").read_text())
NAME = CFG["product_name"]
TAGLINE = CFG["tagline"]
AUTHOR = CFG["author"]
REPO = CFG.get("repo_url", "")
LOG = CFG.get("build_log_url", "")
SITE = CFG.get("site_url", "")

MERCHANT_TABS = [("index.html", "Today"), ("invoices.html", "Invoices"), ("declarations.html", "Export forms"), ("controls.html", "Controls")]
ABOUT_TABS = [("how-it-works.html", "How it works"), ("results.html", "Test results"), ("playbook.html", "Playbook"), ("learning.html", "Learning"), ("judges.html", "For judges")]
DISCLAIMER = "Concept prototype for the Razorpay AI x PM Build Challenge. Not a Razorpay product. All data is made up."
THRESHOLD = 0.80
STAGES = D["stages"]
FX = D["fx"]
ITEMS = sorted(D["items"], key=lambda i: i["rank"])
BY_SLUG = {i["slug"]: i for i in ITEMS}
DEMO_ORDER = ["sl-1039", "sl-1043", "sl-1052-1053", "edf-pack", "sl-1051", "sl-0981", "sl-1047", "sl-1040-1045", "sl-1054", "sl-1046", "quillon", "sl-1044"]
FAVICON = ("data:image/svg+xml," + "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='12' fill='none' stroke='%2315325b' stroke-width='4'/%3E%3Ccircle cx='16' cy='16' r='5' fill='%230f7b5f'/%3E%3C/svg%3E")
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">')


def e(s):
    return html.escape(str(s), quote=True)


def inr_full(n):
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return "₹" + s


def inr_short(n):
    if n >= 1e7:
        return "₹" + format(n / 1e7, ".2f") + " crore"
    if n >= 1e5:
        return "₹" + format(n / 1e5, ".1f") + " lakh"
    return inr_full(n)


def tag(who):
    w = who.lower()
    if "then" in w:
        return '<span class="tag mixed">' + e(who) + "</span>"
    cls = "ai" if w == "ai" else "rule" if w == "rule" else "you" if w == "you" else "none"
    return '<span class="tag ' + cls + '">' + e(who) + "</span>"


def tg(w):
    return '<span class="tg ' + w.lower() + '">' + e(w) + "</span>"


def chip(text, cls=""):
    return '<span class="chip ' + cls + '">' + e(text) + "</span>"


def label(s):
    return {"done": "done", "stuck": "stuck here", "todo": "not yet", "na": "not needed", "wait": "waiting on someone else"}[s]


def journey_text(states):
    return "; ".join(st + " " + label(s) for st, s in zip(STAGES, states))


def journey(states, mini=False):
    cls = "jr mini" if mini else "jr"
    lis = "".join('<li class="' + s + '"><i></i><span>' + e(st) + '</span><span class="sr-only">: ' + e(label(s)) + "</span></li>"
                  for st, s in zip(STAGES, states))
    return '<ol class="' + cls + '" aria-label="Invoice journey: ' + e(journey_text(states)) + '">' + lis + "</ol>"


def layout(active, title, desc, body, head_extra=""):
    def tabs(items, about=False):
        out = []
        for h, t in items:
            cur = ' aria-current="page"' if h == active else ""
            out.append('<li class="about"><a href="' + h + '"' + cur + ">" + e(t) + "</a></li>" if about else '<li><a href="' + h + '"' + cur + ">" + e(t) + "</a></li>")
        return "".join(out)
    nav = tabs(MERCHANT_TABS) + '<li class="sep"></li>' + tabs(ABOUT_TABS, about=True)
    bottom = []
    for h, t in [("index.html", "Today"), ("invoices.html", "Invoices"), ("declarations.html", "Forms"), ("controls.html", "Controls"), ("how-it-works.html", "More")]:
        cur = ' aria-current="page"' if h == active or (t == "More" and active in [a for a, _ in ABOUT_TABS]) else ""
        bottom.append('<li><a href="' + h + '"' + cur + "><i></i>" + e(t) + "</a></li>")
    links = ['<a href="judges.html">For judges</a>', '<a href="llms.txt">Plain-text summary</a>']
    if REPO:
        links.insert(0, '<a href="' + e(REPO) + '">Code, policy and test sets</a>')
    if LOG:
        links.insert(1, '<a href="' + e(LOG) + '">AI build log</a>')
    return "".join([
        "<!doctype html>\n<html lang=\"en-GB\" data-theme=\"light\">\n<head>\n<meta charset=\"utf-8\">\n",
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
        "<title>" + e(title) + " | " + e(NAME) + "</title>\n",
        '<meta name="description" content="' + e(desc) + '">\n',
        '<meta property="og:title" content="' + e(title) + " | " + e(NAME) + '">\n',
        '<meta property="og:description" content="' + e(desc) + '">\n',
        '<meta property="og:type" content="website">\n',
        ('<meta property="og:url" content="' + e(SITE.rstrip('/') + '/' + active) + '">\n') if SITE else '',
        '<meta property="og:image" content="assets/preview.svg">\n',
        '<link rel="icon" href="' + FAVICON + '">\n',
        FONTS + "\n",
        '<link rel="stylesheet" href="assets/style.css">\n',
        ('<script defer src="/_vercel/insights/script.js"></script>\n') if SITE and "vercel.app" in SITE else "",
        head_extra,
        "</head>\n<body>\n",
        '<a class="skip" href="#main">Skip to content</a>\n',
        '<div class="concept">' + e(DISCLAIMER) + "</div>\n",
        '<header class="top"><div class="wrap"><div class="bar"><a class="brand" href="index.html"><i aria-hidden="true"></i>' + e(NAME) + '</a>',
        '<span class="who">' + e(D["merchant"]["business"]) + " · demo morning: " + e(D["today"]) + ", " + e(D["run_time"]) + "</span></div>",
        '<nav class="tabs" aria-label="Main"><ul>' + nav + "</ul></nav></div></header>\n",
        '<nav class="bottom" aria-label="Main, phone"><ul>' + "".join(bottom) + "</ul></nav>\n",
        '<main id="main">\n' + body + "\n</main>\n",
        '<footer class="site-foot"><div class="inner">',
        "<div>" + e(NAME) + " is a concept prototype by " + e(AUTHOR) + " for the Razorpay AI x PM Build Challenge at ISB, October 2026. It is not a Razorpay product and is not affiliated with or endorsed by Razorpay. " + e(TAGLINE) + ".</div>",
        "<div>Every merchant, client, invoice, email and amount here is made up. Rupee amounts use illustrative rates: USD " + format(FX["USD"], ".0f") + ", GBP " + format(FX["GBP"], ".0f") + ", EUR " + format(FX["EUR"], ".0f") + '. Steps marked "simulated" show what would happen next; they did not happen.</div>',
        "<div>" + " · ".join(links) + "</div>",
        "</div></footer>\n",
        '<script src="assets/app.js" defer></script>\n</body>\n</html>\n',
    ])


def write(name, text):
    (DOCS / name).write_text(text)


def amount_bits(it):
    if it.get("ccy"):
        return '<span class="amt">' + e(it["display"]) + '</span><span class="inr">' + inr_full(it["inr"]) + "</span>"
    return '<span class="amt">' + e(it["display"]) + '</span><span class="inr">' + inr_short(it["inr"]) + "</span>"


def next_in_demo(slug):
    if slug not in DEMO_ORDER:
        return None
    i = DEMO_ORDER.index(slug)
    return BY_SLUG[DEMO_ORDER[i + 1]] if i + 1 < len(DEMO_ORDER) else None


def row(it, cta=None):
    level = it["urgency_level"]
    who = []
    for s in it["steps"]:
        if s[0] in ("Rule", "AI") and s[0] not in who:
            who.append(s[0])
    cta = cta or ("Answer" if it["bucket"] == "answer" else "Open" if it["bucket"] == "stopped" else "Review")
    primary = " primary" if it["bucket"] == "prepared" else ""
    return "".join([
        '<li class="row ' + level + '" data-slug="' + it["slug"] + '">',
        '<div class="jcol">' + journey(it["journey"], mini=True) + "</div>",
        '<div class="main"><a class="t" href="item-' + it["slug"] + '.html">' + e(it["title"]) + '</a><p class="l">' + e(it["line"]) + "</p>",
        '<div class="meta"><span class="urg ' + level + '"><b></b>' + e(it["urgency"]) + '</span><span class="kind">' + e(it["kind"]) + "</span>" + " ".join(tg(w) for w in who) + "</div></div>",
        '<div class="side">' + amount_bits(it) + '<a class="btn small' + primary + '" href="item-' + it["slug"] + '.html">' + cta + "</a></div>",
        "</li>",
    ])


def page_today():
    t = D["totals"]
    arrived_pct = t["arrived_inr"] / t["not_home_inr"] * 100
    prepared = [i for i in ITEMS if i["bucket"] == "prepared"]
    answer = [i for i in ITEMS if i["bucket"] == "answer"]
    stopped = [i for i in ITEMS if i["bucket"] == "stopped"]
    first = BY_SLUG[DEMO_ORDER[0]]
    done_rows = "".join("<li><b>" + e(d["invoice"]) + "</b> " + e(d["client"]) + ": " + e(d["display"]) + " (" + inr_full(d["inr"]) + ") home on " + e(d["home"]) + '. <span class="muted">' + e(d["note"]) + "</span></li>" for d in D["done"])
    noact = "".join("<li><b>" + e(d["what"]) + "</b>: " + e(d["display"]) + " on " + e(d["date"]) + '. <span class="muted">' + e(d["note"]) + "</span></li>" for d in D["no_action"])
    body = "".join([
        "<h1>Good morning, " + e(D["merchant"]["owner"]) + "</h1>",
        '<p class="brief">I checked every overseas payment and invoice at ' + e(D["run_time"]) + ". <b>" + inr_short(t["not_home_inr"]) + " is not home yet.</b> ",
        '<span data-count="prepared">' + str(len(prepared)) + "</span> things are ready for your OK, " + '<span data-count="answer">' + str(len(answer)) + "</span> need your answer and " + str(len(stopped)) + " is stopped. Nothing goes out until you say so. ",
        '<a href="item-' + first["slug"] + '.html">Start the demo</a> · <a href="#" data-reset>Reset the demo</a> · <a href="judges.html">For judges</a></p>',
        '<section class="strip" aria-label="Money not home">',
        '<div><div class="lab">Overseas money not home yet</div><div class="big mono">' + inr_full(t["not_home_inr"]) + "</div>",
        '<div class="lab">' + str(t["arrived_count"]) + " stuck payments and " + str(t["not_paid_count"]) + " unpaid invoices</div>",
        '<div class="seg" role="img" aria-label="' + inr_short(t["arrived_inr"]) + " already paid but stuck; " + inr_short(t["not_paid_inr"]) + ' not paid yet"><span class="a" style="width:' + format(arrived_pct, ".1f") + '%"></span><span class="b" style="width:' + format(100 - arrived_pct, ".1f") + '%"></span></div>',
        '<ul class="legend"><li><i class="a"></i><b class="mono">' + inr_short(t["arrived_inr"]) + "</b> paid by clients but not in your bank: waiting for an invoice, an export form, a review or your answer</li>",
        '<li><i class="b"></i><b class="mono">' + inr_short(t["not_paid_inr"]) + "</b> not paid yet: declined cards, a dispute and a deadline (Tidewater\'s second $1,500 invoice joins this once you say which one was paid)</li></ul></div>",
        '<div class="counts"><a href="#ready"><div class="n" data-count="prepared">' + str(len(prepared)) + '</div><div class="l">ready for your OK</div></a>',
        '<a href="#answer"><div class="n" data-count="answer">' + str(len(answer)) + '</div><div class="l">need your answer</div></a>',
        '<a href="#stopped"><div class="n" data-count="stopped">' + str(len(stopped)) + '</div><div class="l">stopped, your call</div></a>',
        '<a href="#home"><div class="n mono">' + inr_short(t["home_14d_inr"]).replace(" lakh", "L") + '</div><div class="l">home in the last 14 days</div></a></div>',
        "</section>",
        '<h2 class="sec" id="ready">Ready for your OK <small>' + str(len(prepared)) + " items, most urgent first · " + tg("Rule") + " is a fixed check · " + tg("AI") + " is a judgement, shown with its confidence · nothing is sent until you approve it</small></h2>",
        '<ul class="list" data-bucket="prepared">' + "".join(row(i) for i in prepared) + "</ul>",
        '<h2 class="sec" id="answer">Needs your answer <small>The agent won\'t guess with money</small></h2>',
        '<ul class="list" data-bucket="answer">' + "".join(row(i) for i in answer) + "</ul>",
        '<h2 class="sec" id="stopped">Stopped, your call</h2>',
        '<ul class="list" data-bucket="stopped">' + "".join(row(i) for i in stopped) + "</ul>",
        '<h2 class="sec" id="done-today">Done this morning <small>Items you approve or answer in this demo move here (needs JavaScript; nothing is sent)</small></h2>',
        '<ul class="list" data-bucket="done"></ul><p class="muted small" data-done-empty>Nothing yet.</p>',
        '<h2 class="sec" id="home">Home recently</h2>',
        '<div class="card"><ul>' + done_rows + '</ul><p class="muted small" style="margin:0">No action needed:</p><ul style="margin-bottom:0">' + noact + "</ul></div>",
        '<div class="callout accent"><p><b>How this list is ordered.</b> Hard deadlines first (a card payment refunds automatically after 3 days; export money is due within nine months), then money blocked by a missing form, then money that has arrived, then declined payments. Each item says what a fixed rule would have done instead. We expect a normal morning to hold none to two items (an assumption the pilot tests); this demo morning packs twelve situations into one day.</p></div>',
    ])
    write("index.html", layout("index.html", "Today", inr_short(t["not_home_inr"]) + " of overseas money not home yet: what the agent prepared this morning, for the owner to approve.", body))


def steps_html(it):
    out = []
    for who, text, conf in it["steps"]:
        meter = ""
        if conf is not None and who != "Rule":
            low = " low" if conf < THRESHOLD else ""
            meter = ('<div class="conf' + low + '"><span class="meter"><span style="width:' + format(conf * 100, ".0f") + '%"></span></span>'
                     "<span>confidence " + format(conf, ".2f") + "</span><span>(asks below " + format(THRESHOLD, ".2f") + ")</span></div>")
        out.append("<li><div>" + tag(who) + "</div><div>" + e(text) + meter + "</div></li>")
    return '<ol class="steps">' + "".join(out) + "</ol>"


def timeline_html(rows):
    lis = "".join('<li><span class="t">' + e(t) + "</span><span>" + e(x) + ('<span class="sim">simulated</span>' if sim else "") + "</span></li>" for t, x, sim in rows)
    return '<ol class="timeline">' + lis + "</ol>"


ANSWER_NOTES = {
    "sl-1052-1053": {"It's SL-1053": "The agent would link the payment to SL-1053 instead, add it to the export form pack and remember the choice.",
                     "Ask Tidewater": "The agent would draft a one-line question to Marcus at Tidewater for your approval, in his working hours."},
    "quillon": {"It's from an existing client": "You pick the client; the agent links the payment and remembers QUILLON DESIGNWORKS as one of their payer names.",
                "Not ours: tell Razorpay support": "Bank transfers can't be refunded through Razorpay, so the agent would prepare a note to Razorpay support with the payment details, for your approval."},
    "sl-1044": {"I'll reply myself": "The agent stays out of it. You can draft your reply here and the agent keeps the invoice on do-not-contact.",
                "Resolved: resume": "The agent would take Halcyon off do-not-contact for SL-1044 and suggest the next step, starting with reminder 2.",
                "I'll write it off in Zoho": "The agent never edits invoices. When the invoice is closed in Zoho, the agent stops tracking it."},
}
NOT_NOW = "Not now snoozes this item until tomorrow morning's run. Deadlines still count down."
NO_SUGGEST = "Don't suggest this tells the agent not to suggest it again for 30 days. A no is a no."


def after_heading(it):
    if it["bucket"] == "prepared":
        return "After you approve"
    if it["bucket"] == "answer":
        return "If you answer “" + it["approve_label"] + "”"
    return "What happens next"


def extra_block(it):
    if it["slug"] != "edf-pack":
        return ""
    rows = [
        ("SL-1045", "3 Oct", "Juniper Ridge Inc, CA", "Product design sprint 2", "$2,400", "$2,400 (in $5,400 with SL-1040), 7 Oct", "P0802 on account: confirm for design"),
        ("SL-1047", "5 Oct", "Larkspur Labs Inc, US", "Website build, sprint 2", "$2,000", "$1,950 ($50 charges), 9 Oct", "P0802 fits"),
        ("SL-1054", "6 Oct", "Fernhill Analytics Ltd, UK", "Data product design: discovery", "£3,200", "£3,200, 9 Oct", "P0802 on account: confirm for design"),
    ]
    trs = "".join('<tr><td class="nowrap"><b>' + e(a) + '</b></td><td class="nowrap">' + e(b) + "</td><td>" + e(c) + "</td><td>" + e(d) + '</td><td class="num">' + e(f) + "</td><td>" + e(g) + "</td><td>" + e(h) + "</td></tr>" for a, b, c, d, f, g, h in rows)
    note = "note-code"
    q = [("Keep P0802 for all three", "The pack goes as prepared. You can change the code with the bank later, but some banks charge for it."),
         ("Use another code for the design invoices", "You pick the code; the agent updates the pack and remembers it for design invoices."),
         ("I'll confirm with ICICI or my CA first", "The agent keeps the pack ready and reminds you tomorrow morning. The three payments stay blocked until the EDF numbers arrive.")]
    btns = "".join('<button class="btn small" type="button" data-explain="' + note + '" data-text="' + e(t) + '">' + e(a) + "</button>" for a, t in q)
    return "".join([
        '<section class="card"><h2>The data prepared for ICICI</h2>',
        '<div class="table-wrap"><table><thead><tr><th>Invoice</th><th>Date</th><th>Client</th><th>Service</th><th class="num">Amount</th><th>Received</th><th>Purpose code</th></tr></thead><tbody>' + trs + "</tbody></table></div>",
        "<p><b>Purpose code question.</b> Two of these are design work, and your account's code is P0802, Software consultancy or implementation. Razorpay's freelancer guide lists P0806 for graphic design; the RBI code list Stripe publishes describes P0806 as \"Other information services\". A wrong code can freeze a remittance, so this is your call. The three answers carry equal weight and nothing is pre-selected:</p>",
        '<div class="actions">' + btns + '<div class="inline-note" id="' + note + '" role="status"></div></div>',
        '<p class="small muted" style="margin:10px 0 0">Fields follow what banks ask for in their EDF request formats; the purpose code column holds a code and the question is carried separately in the file. Confirm against ICICI\'s form. Preview the file: <a href="downloads/edf-pack-sl-1045-1047-1054.csv">edf-pack-sl-1045-1047-1054.csv</a></p></section>',
    ])


def item_page(it):
    slug = it["slug"]
    nxt = next_in_demo(slug)
    facts = "".join("<li>" + e(t) + ' <span class="src">' + e(s) + "</span></li>" for t, s in it["facts"])
    prepared = "".join("<li>" + e(p) + "</li>" for p in it["prepared"])
    limits = "".join("<li>" + e(x) + "</li>" for x in it["limits"])
    note_id = "note-" + slug
    draft = ""
    if it.get("draft"):
        paras = "".join("<p>" + e(p) + "</p>" for p in it["draft"])
        draft = ('<div class="draft"><div class="meta">' + e(it.get("draft_kind", "Draft")) + '</div><div class="subject">' + e(it.get("draft_subject", "")) + '</div><div class="text" id="draft-' + slug + '">' + paras + "</div></div>")
    buttons = []
    explain_lines = []
    if it["bucket"] == "prepared":
        buttons.append('<a class="btn primary" href="item-' + slug + '-done.html">' + e(it["approve_label"]) + "</a>")
        if it.get("draft") and not it.get("optional_draft"):
            buttons.append('<button class="btn" type="button" data-edit="draft-' + slug + '">Edit draft</button>')
        buttons.append('<button class="btn" type="button" data-explain="' + note_id + '" data-text="' + e(NOT_NOW) + '">Not now</button>')
        buttons.append('<button class="btn" type="button" data-explain="' + note_id + '" data-text="' + e(NO_SUGGEST) + '">Don\'t suggest this</button>')
        explain_lines = [NOT_NOW, NO_SUGGEST]
    elif it["bucket"] in ("answer", "stopped"):
        notes = ANSWER_NOTES.get(slug, {})
        for a in it.get("answers", []):
            if it.get("approve_label") == a:
                buttons.append('<a class="btn" href="item-' + slug + '-done.html">' + e(a) + "</a>")
            else:
                buttons.append('<button class="btn" type="button" data-explain="' + note_id + '" data-text="' + e(notes.get(a, "")) + '">' + e(a) + "</button>")
                if notes.get(a):
                    explain_lines.append(a + ": " + notes[a])
    actions = '<div class="actions">' + "".join(buttons) + '<div class="inline-note" id="' + note_id + '" role="status"></div></div>'
    if explain_lines:
        actions += '<p class="explain">' + " ".join(e(x) for x in explain_lines) + "</p>"
    optional = ""
    if it.get("optional_draft"):
        optional = ('<section class="card"><h2>Separate decision: an optional thank-you</h2>' + draft +
                    '<div class="actions"><button class="btn" type="button" data-explain="note-opt-' + slug + '" data-text="In the live product this schedules the thank-you for Ruth\'s working hours after the link is approved. Nothing is sent in this demo.">Send the thank-you too</button>'
                    '<button class="btn" type="button" data-edit="draft-' + slug + '">Edit draft</button>'
                    '<button class="btn" type="button" data-explain="note-opt-' + slug + '" data-text="The thank-you is dropped. The link above is unaffected.">Skip it</button>'
                    '<div class="inline-note" id="note-opt-' + slug + '" role="status"></div></div>'
                    '<p class="explain">Approving the link above sends nothing to the client. This note is a separate choice with equal-weight buttons.</p></section>')
        draft = ""
    after = timeline_html(it["after"]) if it["after"] else '<p class="muted">Nothing happens until you decide.</p>'
    who_line = e(it["client"]) + (" · " + e(it["country"]) if it.get("country") else "")
    invs = ", ".join(it["invoices"]) if it["invoices"] else "No invoice yet"
    next_link = ('<a href="item-' + nxt["slug"] + '.html">Next in the demo: ' + e(nxt["title"]) + "</a>") if nxt else '<a href="index.html">Back to Today</a>'
    level = it["urgency_level"]
    why_cls = "box " + ("high" if level == "high" else "low" if level == "low" else "")
    prepared_title = "Prepared for you" if it["bucket"] == "prepared" else "Your decision"
    body = "".join([
        '<div class="crumbs"><a href="index.html">Today</a> › ' + e(it["kind"]) + " · " + chip(it["urgency"], level if level != "low" else "") + "</div>",
        "<h1>" + e(it["title"]) + "</h1>",
        '<p class="lede">' + e(it["line"]) + "</p>",
        '<div class="card"><div class="head">' + ('<span class="amt">' + e(it["display"]) + '</span><span class="inr">' + inr_full(it["inr"]) + "</span>" if it.get("ccy") else '<span class="amt">' + e(it["display"]) + '</span><span class="inr">worth ' + inr_short(it["inr"]) + "</span>"),
        "<span>" + who_line + "</span><span>" + ("Invoices " if len(it["invoices"]) > 1 else "Invoice ") + e(invs) + "</span></div>" + journey(it["journey"]) + "</div>",
        '<section class="card"><h2>' + prepared_title + "</h2><ul>" + prepared + "</ul>" + draft + actions + "</section>",
        '<div class="why"><div class="' + why_cls + '"><b>Why now.</b> ' + e(it["why_now"]) + "</div>",
        '<div class="box lim"><b>Limits that apply</b><ul>' + limits + '</ul><span class="small muted">Rules of the agent: <a href="controls.html">Controls</a></span></div></div>',
        extra_block(it),
        '<div class="grid-2"><section class="card"><h2>What happened</h2><ul class="facts">' + facts + "</ul></section>",
        '<section class="card"><h2>How the agent decided</h2>' + steps_html(it) + '<p class="fixed"><b>What a fixed rule would do:</b> ' + e(it["baseline"]) + "</p></section></div>",
        optional,
        '<section class="card"><h2>' + after_heading(it) + "</h2>" + after + '<p class="audit" style="margin:10px 0 0">Audit log entry: ' + e(it["audit"]) + "</p>",
        '<p class="small" style="margin:8px 0 0">' + next_link + "</p></section>",
    ])
    write("item-" + slug + ".html", layout("index.html", it["title"], it["line"], body))

    if it["bucket"] in ("prepared", "answer") and it["after"]:
        first_time = it.get("approved_at", it["after"][0][0])
        verb = "Approved" if it["bucket"] == "prepared" else "Answered"
        learned = [x for t, x, _ in it["after"] if t == "Learned"]
        learn_html = '<div class="callout accent"><p><b>Learned:</b> ' + e(" ".join(learned)) + " You can undo this on the <a href=\"learning.html\">Learning</a> page.</p></div>" if learned else ""
        if it.get("download"):
            learn_html += '<section class="card"><h2>Your file</h2><p><a class="btn" href="downloads/' + e(it["download"]) + '" download>Download ' + e(it["download"]) + '</a></p><p class="small muted" style="margin:0">Illustrative file from the demo data.</p></section>'
        remaining = ""
        done_body = "".join([
            '<div class="crumbs"><a href="index.html">Today</a> › <a href="item-' + slug + '.html">' + e(it["kind"]) + "</a> › Done</div>",
            "<h1>" + verb + ": " + e(it["title"]) + "</h1>",
            '<div class="callout ok"><p><b>' + verb + " by " + e(D["merchant"]["owner"]) + " at " + e(first_time) + ".</b> Recorded in the audit log: " + e(it["audit"]) + ' <span data-remaining></span></p></div>',
            '<div class="card">' + journey(it.get("journey_after") or advance(it["journey"])) + "</div>",
            '<section class="card"><h2>What happens now</h2>' + timeline_html(it["after"]) + '<p class="small muted" style="margin:10px 0 0">Steps marked simulated show what would happen next in a live product. In this demo nothing is sent, uploaded or filed.</p></section>',
            learn_html,
            '<p><a class="btn primary" href="' + ("item-" + nxt["slug"] + ".html" if nxt else "index.html") + '">' + ("Next in the demo: " + e(nxt["title"]) if nxt else "Back to Today") + '</a> <a class="btn" href="index.html">Back to Today</a></p>',
            '<script>try{var d=JSON.parse(localStorage.getItem("homeward-done")||"[]");if(d.indexOf("' + slug + '")<0){d.push("' + slug + '");localStorage.setItem("homeward-done",JSON.stringify(d));}}catch(err){}</script>',
        ])
        write("item-" + slug + "-done.html", layout("index.html", verb + ": " + it["title"], it["line"], done_body))


def advance(states):
    out, moved = [], False
    for s in states:
        if s == "stuck" and not moved:
            out.append("done")
            moved = True
        else:
            out.append(s)
    return out


def page_invoices():
    rows = []
    for inv in D["invoices"]:
        link = '<a class="btn small" href="item-' + inv["slug"] + '.html">Open</a>' if inv["slug"] else '<span class="chip ok">Closed</span>'
        rows.append("".join([
            '<li class="row">',
            '<div class="jcol">' + journey(inv["journey"], mini=True) + "</div>",
            '<div class="main"><span class="t">' + e(inv["invoice"]) + " · " + e(inv["client"]) + '</span><p class="l">' + e(inv["service"]) + " · dated " + e(inv["date"]) + '</p><div class="meta"><span class="status-word">' + e(inv["status"]) + "</span></div></div>",
            '<div class="side"><span class="amt">' + e(inv["display"]) + '</span><span class="inr">' + inr_full(inv["inr"]) + "</span>" + link + "</div>",
            "</li>",
        ]))
    legend = ", ".join(e(s) for s in STAGES)
    body = "".join([
        "<h1>Invoices</h1>",
        '<p class="lede">Every overseas invoice, and where it is on its way home. The track follows the journey: ' + legend + ". A ringed step is where it is stuck; a dashed step is one this invoice does not need (invoices dated before 1 October 2026 need no export form). The status word says it in plain words.</p>",
        '<ul class="list">' + "".join(rows) + "</ul>",
        '<p class="small muted">Plus one payment with no invoice yet: $800 from QUILLON DESIGNWORKS (<a href="item-quillon.html">open</a>), and an Upwork payout that needs nothing.</p>',
    ])
    write("invoices.html", layout("invoices.html", "Invoices", "Every overseas invoice and where it is stuck on its way home.", body))


def page_declarations():
    rows = "".join('<li class="row two"><div class="main"><span class="t">' + e(r["invoice"]) + " · " + e(r["client"]) + ", " + e(r["country"]) + '</span><p class="l">' + e(r["service"]) + " · " + e(r["payment"]) + '</p><div class="meta"><span>' + e(r["when"]) + '</span><span class="kind">' + e(r["code"]) + '</span></div></div><div class="side"><span class="amt">' + e(r["display"]) + '</span><span class="inr">' + inr_full(r["inr"]) + "</span></div></li>" for r in D["edf_october"])
    body = "".join([
        "<h1>Export forms</h1>",
        '<p class="lede">Since 1 October 2026, services exporters that are firms declare each export to their bank on an Export Declaration Form (EDF). The agent works out which invoices need one and when, and prepares the data. You submit it; the agent never files with the bank. The form is the same whichever bank you settle to; what differs is when the bank needs it and whether it treats your service as software or as other services, which the agent asks you to confirm.</p>',
        '<div class="grid-3">',
        '<div class="card"><h3>Does ' + e(D["merchant"]["business"]) + " need EDFs?</h3><p><b>Yes.</b> It is an LLP. On 7 October 2026 the RBI said individuals on personal-nature contracts are not covered; firms still are. The EDF applies to every services invoice regardless of its value. RBI's FAQs are pending (none published as of 12 October), and the agent will update this when they arrive.</p></div>",
        '<div class="card"><h3>When</h3><p>Within 30 days after the end of the month of the invoice, so October\'s invoices are due by <b>30 November 2026</b>. One EDF can cover the whole month. Non-software services may instead be declared on or before the payment is received. Only invoices dated on or after 1 October 2026 are covered.</p></div>',
        '<div class="card"><h3>Why some can\'t wait</h3><p>This account settles to ICICI, and while ICICI requires an <b>EDF number before Razorpay captures</b> a MoneySaver bank transfer, three payments already received are blocked until the number exists. An account settling elsewhere files the same form after the money lands.</p></div>',
        "</div>",
        '<div class="callout high"><p><b>Needed now, to release ' + inr_short(BY_SLUG["edf-pack"]["inr"]) + ':</b> SL-1045, SL-1047 and SL-1054. <a href="item-edf-pack.html">Review the pack</a></p></div>',
        '<div class="section-head"><h2>October 2026</h2><span class="count">' + str(len(D["edf_october"])) + " invoices need an EDF</span></div>",
        '<ul class="list">' + rows + "</ul>",
        '<section class="card"><h2>The regulation, in its own words</h2>',
        "<p>RBI Notification FEMA 23(R)/2026-RB, Foreign Exchange Management (Export and Import of Goods and Services) Regulations, 2026, in force from 1 October 2026, amended on 22 September 2026.</p>",
        '<ul class="kv">',
        '<li><b>Who and when (Regulation 3(2))</b><span>A services exporter files the EDF "within 30 days from the end of month in which invoice for services has been raised". One EDF may cover all exports in a month (proviso a). A services exporter other than software "may file on or before the date of receipt of payment" instead (proviso b). The bank may extend the deadline on a reasoned request (proviso c).</span></li>',
        '<li><b>Time to be paid (Regulation 5)</b><span>Export proceeds are due within nine months. The amendment of 22 September 2026 substituted "nine months" for "fifteen months"; Razorpay\'s blog of 8 September 2026 still says fifteen, because it predates the amendment. The bank may allow an extension.</span></li>',
        '<li><b>The ₹10 lakh line (Regulations 4 and 6)</b><span>For an invoice up to ₹10 lakh the bank may close the export entry, or allow a reduction for a shortfall, "based on a declaration from the exporter". This is about documents and closure. It does not exempt any invoice from the EDF itself.</span></li>',
        '<li><b>Unpaid for a year past the due date (Regulation 13)</b><span>The exporter may export only against full advance payment or an irrevocable letter of credit.</span></li>',
        '<li><b>Individuals (RBI, 7 October 2026)</b><span>"the individuals are not included with respect to the reporting requirements for the contracts of a personal nature" (Deputy Governor Rohit Jain, via Business Today). FAQs promised; not yet published.</span></li>',
        '<li><b>ICICI and MoneySaver (Razorpay blog, 21 September 2026)</b><span>"you will be required to file for EDF number before capturing any payment with Razorpay Moneysaver." Razorpay says it is working with ICICI on a smoother EDF generation process. The agent treats this as one bank\'s current operating rule, not as the law.</span></li>',
        "</ul></section>",
        '<section class="card"><h2>Purpose code check</h2>',
        "<p>The account's purpose code: <b>" + e(D["merchant"]["purpose_code"]) + "</b>. Five of October's invoices are design work. Sources disagree on the code for design: Razorpay's freelancer guide lists P0806 for graphic design, while the RBI code list Stripe publishes describes P0806 as \"Other information services\". A wrong code can freeze a remittance, so the agent asks you to confirm with ICICI or your CA rather than guessing.</p></section>",
        '<section class="card"><h2>No EDF needed</h2><p>SL-1036, SL-1038, SL-1039, SL-1040, SL-1044 and SL-1046 are dated before 1 October 2026. The new rule does not cover them, so Razorpay can capture their payments as soon as they are linked.</p></section>',
        '<section class="card"><h2>Who is responsible for what</h2><ul><li>The agent prepares the data from the invoices and the payments it can see, and tracks the deadlines.</li><li>You confirm the purpose code and submit the form; the declaration is yours, so its content is your responsibility, not the agent\'s.</li><li>The bank reports the export and the realisation in EDPMS; the eBRC is then generated by you on the DGFT portal, self-certified against the bank\'s record (DGFT, self-certification of eBRC, 2023). Today you type the EDF number in when the bank gives it, which is not bank confirmation; the right loop is an EDF-number field in the Exporter Dashboard that the partner bank confirms.</li></ul></section>',
        '<section class="card"><h2>Downloads (illustrative)</h2><ul><li><a href="downloads/edf-pack-sl-1045-1047-1054.csv">EDF data for today\'s pack (CSV)</a></li><li><a href="downloads/edf-october-2026.csv">October 2026 EDF data (CSV)</a></li></ul><p class="small muted" style="margin:0">Fields follow what banks ask for in their EDF request formats; confirm against your bank\'s form before submitting.</p></section>',
        '<p class="small muted">Sources: RBI Notification FEMA 23(R)/2026-RB as amended to 22 September 2026 (re-read 12 October 2026); Business Today, 7 October 2026; Razorpay blogs, 21 September and 8 October 2026; Stripe India docs.</p>',
    ])
    write("declarations.html", layout("declarations.html", "Export forms", "Which invoices need an export declaration form, when, what the regulation says, and why three payments are blocked.", body))


def page_playbook():
    groups = []
    first = True
    for g in dict.fromkeys(p["group"] for p in D["playbook"]):
        sits = []
        for p in [x for x in D["playbook"] if x["group"] == g]:
            demo = '<a href="item-' + p["slug"] + '.html">See it in the demo</a>' if p["slug"] else '<span class="muted">Not in the demo</span>'
            sits.append("".join([
                '<div class="sit"><div class="s">' + e(p["situation"]) + " " + tag(p["decides"]) + "</div>",
                "<div><span>How it is spotted</span>" + e(p["signal"]) + "</div>",
                "<div><span>What the agent does</span>" + e(p["does"]) + "</div>",
                "<div><span>It never</span>" + e(p["never"]) + " · " + demo + "</div></div>",
            ]))
        groups.append('<details class="group"' + (" open" if first else "") + "><summary>" + e(g) + ' <span class="muted" style="font-weight:400">' + str(len(sits)) + " situations</span></summary>" + "".join(sits) + "</details>")
        first = False
    shown = len({p["slug"] for p in D["playbook"] if p["slug"]})
    body = "".join([
        "<h1>Playbook</h1>",
        '<p class="lede">Every situation the agent is built to handle: ' + str(len(D["playbook"])) + " of them, in four groups. For each one: how it is spotted, whether a rule or the AI decides, what the agent does, and what it never does. The demo walks through " + str(shown) + " of them. The first group is open; tap the others to open them.</p>",
        '<div class="callout accent"><p><b>Rules first, AI only for judgement.</b> Deadlines, limits and exemptions are rules, because they must never be wrong. The AI reads what needs judgement: messy payer names and references, client replies in other languages, which way to pay, and drafts. Below 0.80 confidence, the agent asks you.</p></div>',
        "".join(groups),
    ])
    write("playbook.html", layout("playbook.html", "Playbook", str(len(D["playbook"])) + " situations the agent handles, and how.", body))


HUMAN = {
    "bank_transfer": "offer a bank transfer", "wallet_link": "offer Apple Pay or Google Pay",
    "retry_card_with_fix": "ask to retry the card with the right address", "ask_when_to_pay": "ask when they would like to pay",
    "wait_until_date": "wait until the date they gave", "stop_dispute": "stop: it is a dispute",
    "owner_sends": "prepare it for the owner to send (client is on do-not-contact)",
    "merchant_action_needed": "offer a bank transfer and fix the account setting",
    "hand_to_owner_limit": "hand to the owner (two reminders already sent)",
    "already_paid": "already paid: stop and look for the payment", "will_pay_on_date": "will pay on a date: pause",
    "dispute": "dispute: stop and hand over", "wrong_contact": "ask the owner to update the contact",
    "out_of_office": "out of office: pause", "asks_bank_details": "send bank details",
    "question_about_invoice": "hand the question to the owner", "stop_contact": "stop contact",
    "payment_failed_again": "offer another way to pay", "no_action": "keep waiting, then remind",
    "suspicious": "suspicious: hand to the owner",
}


def human(x):
    return HUMAN.get(x, x.replace("_", " "))


def pct(a, b):
    return format(a / b * 100, ".0f") + "%"


def load(p):
    return json.loads(p.read_text())


def page_results():
    sets = [("standard", "Standard set", "Written by us from the policy, by a seeded script"),
            ("hard", "Hard set", "Written by a separate AI instance told to break the agent"),
            ("safety", "Safety set", "Instructions hidden in messages and references"),
            ("fresh", "Fresh set", "Written by the second-judge pass without the answer keys, after the build")]
    tasks = (("matching", "Match payments to invoices"), ("declines", "Next way to pay after a decline"), ("replies", "Read client replies"))
    totals = {"agent": [0, 0, 0], "fair": [0, 0, 0], "rules": [0, 0, 0]}  # correct, critical, cases
    pub = {"agent": [0, 0, 0], "fair": [0, 0, 0], "rules": [0, 0, 0]}
    rows = []
    money = {"agent": [0, 0], "fair": [0, 0], "rules": [0, 0]}
    for key, name, desc in sets:
        if key not in S:
            continue
        for task, tname in tasks:
            if task not in S[key]:
                continue
            cells = []
            n = S[key][task]["agent"]["cases"]
            for who in ("agent", "fair", "rules"):
                r = S[key][task][who]
                if task == "matching":
                    c = r["correct_link"] + r["correct_hold"]
                    crit = r["wrong_link"]
                    money[who][0] += r["released_inr"]
                    money[who][1] += r["wrong_inr"]
                else:
                    c = r["correct"]
                    crit = r["critical"]
                totals[who][0] += c
                totals[who][1] += crit
                totals[who][2] += n
                if key != "fresh":
                    pub[who][0] += c
                    pub[who][1] += crit
                    pub[who][2] += n
                cells.append('<td class="num">' + str(c) + " of " + str(n) + (" · " + str(crit) + " serious" if crit else "") + "</td>")
            rows.append("<tr><td>" + e(name) + "</td><td>" + e(tname) + "</td>" + "".join(cells) + "</tr>")
    # confidence histogram
    bins = {"below 0.80": 0, "0.80 to 0.89": 0, "0.90 to 0.94": 0, "0.95 and above": 0}
    n_conf = 0
    low = {"standard": 0, "hard": 0, "safety": 0, "fresh": 0}
    for f in sorted((ROOT / "eval" / "outputs").glob("agent_*.json")):
        setname = "standard"
        for s in ("hard", "safety", "fresh"):
            if f.name.startswith("agent_" + s + "_"):
                setname = s
        for r in load(f):
            c = r.get("confidence")
            if c is None:
                continue
            n_conf += 1
            if c < 0.80:
                bins["below 0.80"] += 1
                low[setname] += 1
            elif c < 0.90:
                bins["0.80 to 0.89"] += 1
            elif c < 0.95:
                bins["0.90 to 0.94"] += 1
            else:
                bins["0.95 and above"] += 1
    mxb = max(bins.values()) or 1
    hist = "".join('<div class="col"><b>' + str(v) + '</b><div class="bar"><span style="width:' + format(v / mxb * 100, ".0f") + '%"></span></div>' + e(k) + "</div>" for k, v in bins.items())
    # disagreements on the fresh set
    fresh_rows = []
    if "fresh" in S:
        fin = {}
        for task in ("matching", "declines", "replies"):
            for r in load(ROOT / "eval" / "inputs" / ("fresh_" + task + ".json")):
                fin[r["id"]] = r
        for task in ("matching", "declines", "replies"):
            for who, wname in (("agent", "Agent"), ("fair", "Fair rules")):
                for er in S["fresh"][task][who]["errors"]:
                    a, p = er["answer"], er["prediction"]
                    if task == "matching":
                        ans = ("link " + ", ".join(a.get("invoices", []))) if a["decision"] == "link" else "ask (" + a.get("reason_code", "") + ")"
                        pred = ("link " + ", ".join(p.get("invoices", []))) if p["decision"] == "link" else "ask"
                        case = fin[er["id"]]["payment"]["payer_name"] + " paid " + fin[er["id"]]["payment"]["currency"] + " " + format(fin[er["id"]]["payment"]["amount"], ",.2f") + " with reference “" + fin[er["id"]]["payment"]["reference"] + "”"
                    elif task == "declines":
                        ans, pred = human(a["route"]), human(p["route"])
                        case = fin[er["id"]]["decline_message"]
                    else:
                        ans, pred = human(a["label"]), human(p["label"])
                        case = "Client wrote: “" + fin[er["id"]]["reply"] + "”"
                    fresh_rows.append("<tr><td>" + e(er["id"]) + "</td><td>" + e(wname) + "</td><td>" + e(case) + "</td><td>" + e(pred) + "</td><td>" + e(ans) + "</td></tr>")
    fresh_table = ('<div class="table-wrap"><table><thead><tr><th>Case</th><th>Who</th><th>Situation</th><th>Decision</th><th>Answer key</th></tr></thead><tbody>' + "".join(fresh_rows) + "</tbody></table></div>") if fresh_rows else "<p>No disagreements.</p>"
    # examples of naive rule mistakes (kept from v1)
    rin = {r["id"]: r for r in load(ROOT / "eval" / "inputs" / "replies.json")}
    ex = []
    for er in S["standard"]["replies"]["rules"]["errors"]:
        if er["critical"]:
            ex.append(("Client wrote: “" + rin[er["id"]]["reply"] + "”", "Naive rules: " + human(er["prediction"]["label"]), "Right: " + human(er["answer"]["label"])))
    hm = {r["id"]: r for r in load(ROOT / "eval" / "inputs" / "hard_matching.json")}
    for er in S["hard"]["matching"]["rules"]["errors"]:
        if er["type"] != "missed":
            p = hm[er["id"]]["payment"]
            ex.append((p["payer_name"] + " paid " + p["currency"] + " " + format(p["amount"], ",.0f") + " with reference “" + p["reference"] + "”, an invoice that belongs to a different client with a similar name.", "Naive rules: linked it to " + ", ".join(er["prediction"]["invoices"]), "Right: ask the owner (the evidence conflicts)"))
    ex_rows = "".join("<tr><td>" + e(a) + "</td><td>" + e(b) + "</td><td>" + e(c) + "</td></tr>" for a, b, c in ex[:6])

    def bar(who, v, mx, name):
        return '<div class="barrow ' + who + '"><span>' + name + '</span><span class="track"><span style="width:' + format(v / mx * 100, ".1f") + '%"></span></span><span class="nowrap mono">' + inr_short(v) + "</span></div>"
    mx = max(money["agent"][0], 1)
    ag, fa, ru = totals["agent"], totals["fair"], totals["rules"]
    body = "".join([
        "<h1>Test results</h1>",
        '<p class="lede">Before trusting an agent with money, test it on cases where the right answer is known, and compare it with what rules alone would do. A separate AI instance played the agent: it saw only the policy and the case inputs, never the answers. Two rule sets ran on the same cases: a naive one (exact matches and keywords) and a fair one, written from the policy by a competent engineer without a model.</p>',
        '<div class="kpis">',
        '<div class="kpi"><div class="n">' + str(ag[1]) + " · " + str(fa[1]) + " · " + str(ru[1]) + '</div><div class="l">serious mistakes across ' + str(ag[2]) + " cases: agent · fair rules · naive rules</div></div>",
        '<div class="kpi"><div class="n">' + inr_short(money["rules"][1]) + '</div><div class="l">linked to the wrong invoice by the naive rules (agent: ' + inr_short(money["agent"][1]) + ", fair rules: " + inr_short(money["fair"][1]) + ")</div></div>",
        '<div class="kpi"><div class="n">' + str(ag[0]) + " of " + str(ag[2]) + '</div><div class="l">agent decisions that matched the answer key (a policy-compliance check, see below)</div></div>',
        '<div class="kpi"><div class="n">' + str(fa[0]) + " · " + str(ru[0]) + '</div><div class="l">fair rules · naive rules matched, of ' + str(ag[2]) + "</div></div>",
        "</div>",
        '<div class="callout warn"><p><b>Read this before trusting the numbers.</b> The three published sets (190 cases) were written by AI from the same policy, so they test whether the agent follows its rules on clean, labelled cases. A fair rule set written from the policy matches the agent on all 190, which is the honest finding: where the input is structured and the policy is written down, rules are enough, and the product uses rules there. The model earns its place on what these cases cannot hold: real decline text, real email threads in other languages, invoice PDFs and bank narrations. The fresh set (36 cases, written after the build without the keys) is the first look at that gap: the agent disagreed with the key once, the fair rules twice. A pilot with real exporters and a holdout group is the real test.</p></div>',
        '<section class="card"><h2>Money linked to the right invoice (all matching cases)</h2><div class="bars">' + bar("agent", money["agent"][0], mx, "Agent") + bar("fair", money["fair"][0], mx, "Fair rules") + bar("rules", money["rules"][0], mx, "Naive rules") + "</div>",
        '<p class="small muted" style="margin:6px 0 0">The agent linked ' + inr_short(money["agent"][0]) + " correctly and nothing wrongly; the fair rules " + inr_short(money["fair"][0]) + " and " + inr_short(money["fair"][1]) + " where the policy says ask; the naive rules " + inr_short(money["rules"][0]) + " and " + inr_short(money["rules"][1]) + " to the wrong invoice.</p></section>",
        '<div class="table-wrap"><table><thead><tr><th>Set</th><th>Task</th><th class="num">Agent</th><th class="num">Fair rules</th><th class="num">Naive rules</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>",
        '<p class="small muted">A serious mistake is linking money where the policy says ask or to the wrong invoice, or carrying on contacting a client who has disputed, asked to stop, already paid, or sent a message trying to manipulate the agent. The fair rule set was written with sight of the inputs but not the answer keys, and was not changed after the fresh set was run.</p>',
        '<div class="section-head"><h2>The fresh set: every disagreement</h2><span class="count">36 cases written by the second-judge pass without the keys</span></div>',
        fresh_table,
        '<p class="small muted">The agent\'s one disagreement is a gap in the policy, not a wrong action: both labels mean "keep waiting". The fair rules asked where the key links (a transposed reference) and linked where the key asks (a single exact match that also equals the sum of two other invoices). The fresh set also exposed three ambiguities in the policy, now written down in policy section 12.</p>',
        '<div class="section-head"><h2>How sure the agent was</h2><span class="count">' + str(n_conf) + " decisions with a confidence</span></div>",
        '<div class="card"><div class="hist">' + hist + '</div><p class="small muted" style="margin:10px 0 0">Confidence is the model\'s own estimate, not a measured error rate. Below 0.80 the agent asks instead of acting: that happened on ' + str(low["standard"]) + ' standard cases (the 16 built to be ambiguous and one reply), ' + str(low["fresh"]) + ' fresh cases and none in the hard or safety sets (hard-set minimum 0.82). The threshold is tuned in the pilot against the wrong-match rate.</p></div>',
        '<div class="section-head"><h2>What the naive rules got wrong</h2><span class="count">Why "exact match plus keywords" is not enough</span></div>',
        '<div class="table-wrap"><table><thead><tr><th>Situation</th><th>What the rules did</th><th>Right action</th></tr></thead><tbody>' + ex_rows + "</tbody></table></div>",
        '<section class="card"><h2>How the test was run</h2><ol>',
        "<li><b>Policy:</b> sections 1 to 10 of the agent's rulebook were the only instruction the model received (v1 for the standard and hard sets, v1.1 with the untrusted-content section for the safety and fresh sets).</li>",
        '<li><b>Standard set (120 cases):</b> generated by a seeded script with an answer key: 60 payments to match, 30 declined payments, 30 client replies, including traps such as "We dispute nothing, payment is scheduled for the 15th".</li>',
        "<li><b>Hard set (60 cases):</b> written by a separate AI instance told to break the agent: garbled payer names, look-alike clients, bank charges at the limit, forwarded email chains, sarcasm, replies in German, French, Spanish and Dutch.</li>",
        "<li><b>Safety set (10 cases):</b> instructions hidden in client emails and payment references, a look-alike email domain, a fake verification link, plus normal controls.</li>",
        "<li><b>Fresh set (36 cases):</b> written on 12 October by the second-judge pass with only the policy in view, keyed by applying the policy literally, then played blind by another fresh instance.</li>",
        "<li><b>Blind runs:</b> a fresh AI instance received only the policy and the inputs, and wrote one decision per case with its confidence and reason.</li>",
        "<li><b>Two rule baselines:</b> naive (exact invoice number and amount, or exact client name and amount; keywords for declines and replies) and fair (fuzzy invoice numbers, bank-charge tolerance, sums, aliases, a decline-code table, phrase rules with negation and a small multilingual vocabulary).</li>",
        "<li><b>Scoring:</b> a script compares all three with the answer keys. Inputs, answer keys, outputs and the scoring code are published with the prototype.</li>",
        "</ol></section>",
    ])
    write("results.html", layout("results.html", "Test results", "Blind tests of the agent against two rule baselines, with every disagreement shown.", body))


def page_learning():
    L = D["learning"]
    routes = "".join("<tr><td>" + e(a) + "</td><td>" + e(b) + '</td><td class="num">' + e(c) + "</td></tr>" for a, b, c in L["routes"])
    aliases = "".join("<tr><td><b>" + e(a) + "</b></td><td>" + e(b) + "</td><td>" + e(c) + '</td><td><button class="btn small" data-explain="undo-note" data-text="In the product, Undo removes this learned name and the agent stops using it at the next run; the audit log keeps the record. In this demo nothing is stored.">Undo</button></td></tr>' for a, b, c in L["aliases"])
    tone = "".join("<li>" + e(x) + "</li>" for x in L["tone"])
    nos = "".join("<tr><td>" + e(a) + "</td><td>" + e(b) + "</td><td>" + e(c) + "</td></tr>" for a, b, c in L["nos"])
    body = "".join([
        "<h1>Learning</h1>",
        '<p class="lede">The agent gets better from outcomes and from your corrections, and you can see and undo everything it has learned. The numbers on this page are synthetic history for the demo.</p>',
        '<section class="card"><h2>The loop, in one paragraph</h2><p>Three signals feed it: outcomes (did the client pay within 7 days of a note; was a match confirmed or corrected; was a draft sent, edited or rejected), your edits, and your answers. They change only the choice within what the rules allow: which way to pay to offer first where the policy allows more than one, the wording of drafts, the lean on an ambiguous match, and payer names remembered once you confirm them. A learned preference is used after at least five outcomes of the same kind or one explicit confirmation from you. It never changes the clocks, the limits, the stop rules, the 0.80 threshold or which invoices need an export form. Policy section 11 is the rule.</p></section>',
        '<section class="card"><h2>Which way to pay works, by decline type</h2><div class="table-wrap"><table><thead><tr><th>Decline</th><th>What the client was offered</th><th class="num">Paid within 7 days</th></tr></thead><tbody>' + routes + '</tbody></table></div><p class="small muted" style="margin:0">After a 3-D Secure failure the policy allows a wallet or a bank transfer; these outcomes decide which is offered first. After a cross-border block the route is fixed by rule (a bank transfer); the outcomes only confirm it.</p></section>',
        '<section class="card"><h2>Payer names it has learned</h2><div class="table-wrap"><table><thead><tr><th>Name on the payment</th><th>Means</th><th>Source</th><th></th></tr></thead><tbody>' + aliases + '</tbody></table></div><p id="undo-note" class="inline-note" aria-live="polite"></p></section>',
        '<section class="card"><h2>Your writing style</h2><ul>' + tone + "</ul></section>",
        '<section class="card"><h2>Things you said no to</h2><div class="table-wrap"><table><thead><tr><th>Suggestion</th><th>You said no</th><th>Status</th></tr></thead><tbody>' + nos + "</tbody></table></div></section>",
        '<section class="card"><h2>Undo, and what happens after a wrong link</h2><p>Every learned item has an undo here (in the demo the Undo buttons only explain; nothing is stored). If you approve a link and later correct it, the agent unlinks it before capture, or after capture prepares a correction note to Razorpay support and your bank for your approval; it demotes the payer name it learned from that match; and auto-approve switches off until 20 more matches are confirmed. The audit log keeps both entries; nothing is rewritten.</p></section>',
        '<section class="card"><h2>Earning more trust</h2><p>The agent\'s last 31 matches were all confirmed as right when you approved them (synthetic). After 20, the agent offers to approve one low-risk step by itself: uploading an invoice that matches at 0.98 or above. It stays off until you switch it on in <a href="controls.html">Controls</a>, and everything it does is still logged.</p></section>',
    ])
    write("learning.html", layout("learning.html", "Learning", "What the agent has learned, what learning may change, and how to undo it.", body))


def page_controls():
    rows = []
    for name, val, note in D["settings"]:
        if val in ("On", "Off"):
            pressed = "true" if val == "On" else "false"
            ctl = '<button class="toggle" type="button" aria-pressed="' + pressed + '">' + val + "</button>"
        else:
            ctl = '<span class="val">' + e(val) + "</span>"
        rows.append('<div class="setting"><div><b>' + e(name) + '</b><div class="small muted">' + e(note) + "</div></div><div>" + ctl + "</div></div>")

    def who_tag(w):
        return tag(w) if w in ("Rule", "AI", "You", "AI, then rule") else '<span class="tag none">' + e(w) + "</span>"
    audit = "".join('<li><span class="t">' + e(t) + "</span><span>" + who_tag(w) + "</span><span>" + e(x) + "</span></li>" for t, w, x in D["audit"])
    principles = [
        ("“No agent takes an irreversible action without explicit merchant approval.”", "Review first is on; every message, upload and share needs your approval; the agent never files with a bank or refunds."),
        ("“The ceiling is the merchant’s ceiling.”", "Two reminders per decline, client hours, the confidence threshold and the do-not-contact list are yours to set; the agent never goes past them."),
        ("“A no is a no.”", "A suggestion you decline is not made again for 30 days; a client who asks to stop is never contacted again."),
        ("“Every single action is logged with a full audit trail.”", "The log below records every action, who decided (rule, AI or you) and who approved."),
        ("No dark patterns.", "Answer buttons carry equal weight, nothing is pre-selected, and client notes never use false urgency."),
    ]
    prin = "".join('<li><b>' + e(a) + "</b><span>" + e(b) + "</span></li>" for a, b in principles)
    perms = [
        ("Razorpay payments and MoneySaver", "Read payment attempts, decline reasons, authorised payments, transfers, references and settlement status; upload an invoice to a payment after approval", "Granted in Agent Studio"),
        ("Email", "Send a note as priya@saffronloop.example after approval; read only the replies to those notes", "Granted by you, revocable"),
        ("Zoho Books", "Read invoices and clients; never write", "Read-only token"),
        ("Google Drive “Contracts”", "Read only when you approve a document pack", "Read-only, one folder"),
        ("Your bank", "Nothing; you enter EDF numbers and submit forms yourself", "No access"),
        ("Who may approve", "Any designated partner of the firm; the person who prepared an item by hand may not also auto-approve it", "Maker and checker"),
    ]
    perm_rows = "".join("<tr><td><b>" + e(a) + "</b></td><td>" + e(b) + "</td><td>" + e(c) + "</td></tr>" for a, b, c in perms)
    body = "".join([
        "<h1>Controls</h1>",
        '<p class="lede">You set the limits; the agent never goes past them. Changes take effect at the next run.</p>',
        '<div class="grid-2"><section class="card"><h2>Settings</h2>' + "".join(rows) + '<div class="inline-note" id="settings-note" role="status">Demo only: settings don\'t save in this prototype.</div></section>',
        "<div>",
        '<section class="card"><h2>Pause the agent</h2><p>Paused, the agent keeps the list up to date but prepares and sends nothing.</p><button class="toggle" type="button" aria-pressed="false" data-on="Paused" data-off="Running">Running</button> <a class="btn small" href="rules-only.html" style="margin-left:8px">See the rules-only mode</a></section>',
        '<section class="card"><h2>What it never does</h2><ul><li>Sends a message, uploads a document or shares a file without your approval.</li><li>Files with a bank, refunds money or promises a date for a bank or Razorpay action.</li><li>Shares client emails or chats.</li><li>Follows instructions written inside client messages or payment references.</li><li>Contacts a client outside their working hours, on their public holidays, more than twice per decline, or after a dispute.</li><li>Sends card numbers or bank statements to the model; it sees payer names, references, amounts, invoices and replies, nothing more.</li></ul></section>',
        "</div></div>",
        '<section class="card"><h2>Razorpay\'s own agent principles, and where each one lives here</h2><ul class="kv">' + prin + '</ul><p class="small muted" style="margin:8px 0 0">Quotes from Razorpay\'s Agent Studio principles (Razorpay blog, 30 March 2026).</p></section>',
        '<section class="card"><h2>What the agent may touch (a proposal for how Agent Studio would grant it)</h2><div class="table-wrap"><table><thead><tr><th>System</th><th>What</th><th>How granted</th></tr></thead><tbody>' + perm_rows + "</tbody></table></div></section>",
        '<div class="section-head"><h2>Audit log</h2><span class="count">Every action, who decided, and who approved</span></div>',
        '<ul class="log">' + audit + "</ul>",
    ])
    write("controls.html", layout("controls.html", "Controls", "The limits the agent works within, Razorpay's agent principles as switches, and its audit log.", body))


def page_rules_only():
    ai_items = [i for i in ITEMS if any(s[0] == "AI" for s in i["steps"])]
    rule_items = [i for i in ITEMS if not any(s[0] == "AI" for s in i["steps"])]
    body = "".join([
        '<div class="crumbs"><a href="controls.html">Controls</a> › Rules-only mode</div>',
        "<h1>If the AI service is down</h1>",
        '<p class="lede">The agent keeps running on rules alone. Clocks, limits, exemptions and exact matches still work; anything that needs judgement waits, and the list says so. This page shows this morning in that mode.</p>',
        '<div class="callout high"><p><b>AI service unavailable since 08:55.</b> Drafts, fuzzy matches and reply reading are paused. Deadlines still count down. Nothing is guessed.</p></div>',
        '<h2 class="sec">Still prepared by rules alone</h2><ul class="list">' + "".join(row(i) for i in rule_items) + "</ul>",
        '<h2 class="sec">Waiting for the AI service <small>Shown with the facts, without a suggestion</small></h2><ul class="list">' + "".join(row(i, cta="Facts only") for i in ai_items) + "</ul>",
        '<div class="callout accent"><p>When the service returns, the agent re-runs the morning and the prepared items reappear. Nothing that was waiting is sent without your approval.</p></div>',
    ])
    write("rules-only.html", layout("controls.html", "Rules-only mode", "What still works when the AI service is down: clocks, limits and exact matches.", body))


def diagram():
    nodes = STAGES
    w, h, bw, bh, gap, y = 980, 250, 128, 46, 42, 40
    x0 = (w - (6 * bw + 5 * gap)) / 2
    parts = ['<svg class="diagram" viewBox="0 0 980 250" role="img" aria-labelledby="dg-t dg-d">',
             '<title id="dg-t">The invoice journey</title>',
             '<desc id="dg-d">Six steps: Sent, Paid, Linked, Declared, In bank, Closed. Under Paid: a declined payment loops back through another way to pay. Under Linked: money waiting for an invoice or with a different payer name or amount is matched. Under Declared: the export form is prepared. Under In bank: a review pack is shared.</desc>',
             '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead" d="M0 0L10 5L0 10z"/></marker></defs>']
    centers = []
    for i, n in enumerate(nodes):
        x = x0 + i * (bw + gap)
        centers.append(x + bw / 2)
        parts.append('<g class="node"><rect x="' + format(x, ".0f") + '" y="' + str(y) + '" width="' + str(bw) + '" height="' + str(bh) + '" rx="10"/><text x="' + format(x + bw / 2, ".0f") + '" y="' + str(y + 29) + '" text-anchor="middle">' + e(n) + "</text></g>")
        if i < 5:
            parts.append('<path class="arrow" d="M' + format(x + bw + 4, ".0f") + " " + format(y + bh / 2, ".0f") + " H" + format(x + bw + gap - 6, ".0f") + '" marker-end="url(#ah)"/>')
    sides = [(1, "Declined: another", "way to pay"), (2, "Waiting for invoice,", "odd name or amount"), (3, "Export form", "prepared for you"), (4, "Review: document", "pack for approval")]
    for idx, l1, l2 in sides:
        cx = centers[idx]
        parts.append('<path class="arrow" d="M' + format(cx, ".0f") + " " + str(y + bh + 4) + " V" + str(y + bh + 46) + '" marker-end="url(#ah)"/>')
        parts.append('<g class="node side"><rect x="' + format(cx - 80, ".0f") + '" y="' + str(y + bh + 52) + '" width="160" height="58" rx="10"/><text class="label" x="' + format(cx, ".0f") + '" y="' + str(y + bh + 76) + '" text-anchor="middle">' + e(l1) + '</text><text class="label" x="' + format(cx, ".0f") + '" y="' + str(y + bh + 96) + '" text-anchor="middle">' + e(l2) + "</text></g>")
    parts.append('<text class="label" x="' + format(w / 2, ".0f") + '" y="' + str(h - 14) + '" text-anchor="middle">Each side box is where money gets stuck today, and where the agent prepares the fix for your approval.</text>')
    parts.append("</svg>")
    return "".join(parts)


QUOTES = [
    ("Razorpay is really bad for international transactions , very high payment failures and such a poor support they have .", "An Indian exporter reviewing Razorpay on Trustpilot, 19 September 2026; the same review says they opened accounts with two rival providers"),
    ("Every time the details of my card get altered by the platform and the payment fails.", "An overseas client in New Zealand paying an Indian firm, Trustpilot, 17 September 2026; she adds that she has already used another platform"),
    ("placing my account under review and holding my second invoice payment", "An Indian IT firm reviewing Razorpay on Trustpilot, 29 April 2025"),
    ("Several follow-ups and branch visits were needed for each FIRA, which interfered with operations", "An exporter quoted in the Economic Times, 25 February 2026"),
]


def page_how():
    clocks = [
        ("A card payment not captured within 3 days of its creation is refunded automatically (the demo counts from the authorisation, which is the same moment for these payments)", "Razorpay docs, capture settings (re-read 12 Oct 2026)"),
        ("International payments are captured only with an invoice; MoneySaver bank transfers need an invoice and buyer details, then capture within 60 minutes and settle T+1", "Razorpay docs"),
        ("While ICICI requires it, accounts settling to ICICI need an EDF number before a MoneySaver payment is captured", "Razorpay blog, 21 Sep 2026 (re-read 12 Oct 2026)"),
        ("Firms file an EDF for services invoices dated on or after 1 Oct 2026, within 30 days after the month ends, or for non-software services on or before receipt of payment", "RBI FEMA 23(R)/2026-RB, Reg. 3(2)"),
        ("Individuals on personal-nature contracts are not required to report; FAQs pending", "RBI, via Business Today, 7 Oct 2026"),
        ("Export money is due within nine months (amended from fifteen on 22 Sep 2026); the bank can extend on request", "RBI FEMA 23(R)/2026-RB, Reg. 5"),
        ("Up to ₹10 lakh per invoice, closure and shortfalls can be handled by the exporter's declaration; the EDF itself applies regardless of value", "RBI FEMA 23(R)/2026-RB, Regs. 4 and 6"),
        ("Address checks apply only to US, UK and Canada cards", "Razorpay docs, AVS"),
        ("Platform payouts (Amazon, Upwork, Freelancer) need no invoice upload; bank transfers cannot be refunded through Razorpay", "Razorpay docs"),
    ]
    clock_rows = "".join("<tr><td>" + e(a) + "</td><td>" + e(b) + "</td></tr>" for a, b in clocks)
    split = [
        ("Deadlines, limits, exemptions, do-not-contact, exact matches, ordering the list, picking the route once the decline is classified", "Rule", "Must never be wrong, and must be explainable"),
        ("Matching a payment when the payer, amount or reference differs from the invoice", "AI", "Parent companies, payment services, typos, bank charges, several invoices in one transfer"),
        ("Reading client replies and decline messages", "AI", "Any wording or language; negations like \"we dispute nothing, payment is on the 15th\"; free-text decline reasons"),
        ("Choosing between allowed ways to pay, and the second choice in a note", "AI", "Client's history and device, within what the rule allows"),
        ("Drafting notes, letters and packs", "AI", "In your tone, short, for your approval"),
        ("Approving anything that leaves the building", "You", "Maker prepares, checker approves"),
    ]
    split_rows = "".join("<tr><td>" + e(a) + "</td><td>" + tag(b) + "</td><td>" + e(c) + "</td></tr>" for a, b, c in split)
    reads = [
        ("Razorpay payments", "Card attempts and decline reasons, authorised payments, MoneySaver transfers, settlements, FIRAs", "Read"),
        ("Zoho Books", "Invoices and client details", "Read only"),
        ("Replies to the agent's notes", "Only replies to notes you approved", "Read"),
        ("Google Drive \"Contracts\"", "Only when you approve a document pack", "Read only"),
        ("Your bank (EDF status)", "You mark EDF numbers as received", "You enter"),
    ]
    read_rows = "".join("<tr><td><b>" + e(a) + "</b></td><td>" + e(b) + "</td><td>" + e(c) + "</td></tr>" for a, b, c in reads)
    fails = [
        ("AI service down", "Runs on rules only: deadlines, limits and exact matches keep working; drafts pause. See the rules-only mode."),
        ("Confidence below 0.80", "Asks you, showing its lean and the evidence."),
        ("You approved a link to the wrong invoice", "Before capture: unlinks and asks again. After capture: prepares a correction note to Razorpay support and the bank for your approval; demotes the learned payer name; switches auto-approve off until 20 more matches are confirmed."),
        ("Zoho disconnected", "Asks you to upload invoices; never invents invoice data."),
        ("A client message tries to instruct the agent or redirect documents", "Marked suspicious; messages to that client pause until you confirm."),
        ("Stuck with Razorpay or the bank", "Prepares a support case with the evidence; never promises their dates."),
        ("Rules change (RBI FAQs are pending)", "Rules are versioned against their source; the agent shows which version it used."),
    ]
    fail_rows = "".join("<tr><td><b>" + e(a) + "</b></td><td>" + e(b) + "</td></tr>" for a, b in fails)
    quotes = "".join("<blockquote><p>“" + e(q) + "”</p><cite>" + e(c) + "</cite></blockquote>" for q, c in QUOTES)
    today_steps = [
        ("A transfer arrives", "Priya learns from a Razorpay email or a dashboard check that a MoneySaver transfer is waiting; she finds the invoice in Zoho and uploads it by hand with the buyer details. Documented: Razorpay docs on invoice upload.", "The agent finds the invoice, matches it even when the payer or amount differs, and prepares the upload for one tap."),
        ("A client's card fails", "The client's bank declines a cross-border card; nobody tells the client another way to pay, so the invoice goes quiet until she notices. Documented: Razorpay's own blogs put international card success at 70 to 80%.", "The agent reads the decline, picks the next way to pay from the client's history, and drafts the note."),
        ("Razorpay's review team asks for documents", "She searches Drive for the contract and the delivery proof and replies through a ticket. Assumption, to validate in the pilot.", "The agent reads the request, picks the documents, and shares only what you approve, never client chats."),
        ("The export form", "Her CA asks what each October invoice was for and which purpose code applies; the month-end filing and the nine-month clock live in a spreadsheet. Documented: RBI regulation; founders' reactions in Business Today, 6 Oct 2026.", "The agent lists which invoices need an EDF and when, prepares the data, flags the code question, and tracks the clocks."),
        ("FIRA and short payments", "Bank charges leave invoices short; FIRAs need follow-ups at some banks. Documented: Economic Times, 25 Feb 2026; Inc42, 8 Oct 2026.", "The agent records charges within the policy caps and prepares the declaration for the shortfall."),
    ]
    today_rows = "".join("<tr><td><b>" + e(a) + "</b></td><td>" + e(b) + "</td><td>" + e(c) + "</td></tr>" for a, b, c in today_steps)
    sizing = [
        ("Overseas inflow per exporter per year", "$10,000", "$20,000", "$36,000", "Base: Skydo, $1bn across 50,000+ businesses (CXO Digital Pulse, 11 Aug 2026); low and high are assumptions"),
        ("Share paid by card", "50%", "50%", "50%", "Razorpay blog, 24 Jun 2024"),
        ("Card value failing at first attempt", "5%", "15%", "25%", "Razorpay newsroom claims 95% success; Razorpay blogs say international cards often drop to 70 to 80%"),
        ("Failed value the agent wins back", "15%", "35%", "55%", "Razorpay blog on automated retries (15 to 20%); Stripe Billing (55%); base is an assumption"),
        ("Won back per exporter per year", "₹3,300", "₹46,200", "₹2.18 lakh", "Arithmetic at ₹88 per dollar"),
        ("Released from document holds, about 10 days sooner", "₹44,000", "₹2.64 lakh", "₹9.5 lakh", "Assumption: 5 to 30% of inflow waits for documents"),
        ("Razorpay's fee on the money won back", "₹33", "₹924", "₹6,534", "1% on transfers, 3% on cards (Razorpay pricing blog)"),
        ("Razorpay's list fees on the whole inflow", "₹17,600", "₹35,200", "₹63,360", "Same pricing"),
    ]
    sizing_rows = "".join("<tr><td>" + e(a) + '</td><td class="num">' + e(b) + '</td><td class="num">' + e(c) + '</td><td class="num">' + e(d) + "</td><td>" + e(f) + "</td></tr>" for a, b, c, d, f in sizing)
    body = "".join([
        "<h1>How it works</h1>",
        '<div class="reading">Reading pages: <a href="judges.html">For judges</a> · <a href="results.html">Test results</a> · <a href="playbook.html">Playbook</a> · <a href="learning.html">Learning</a> · <a href="rules-only.html">Rules-only mode</a></div>',
        '<p class="lede">' + e(NAME) + " is a concept agent for Razorpay's Agent Studio. It works for small Indian services firms paid by overseas clients, and its unit is the invoice, not the payment: an invoice is done only when the money is paid, linked, declared, in the bank and closed.</p>",
        '<section class="card"><h2>The invoice journey</h2>' + diagram() + "</section>",
        '<section class="card"><h2>What the merchants say</h2>' + quotes + '<p class="small muted" style="margin:0">These are public reviews and press quotes, verified at source on 12 October 2026 and cited by role and date. No merchant was interviewed for this entry: it is desk research, and the pilot below is how that gap closes. The Skydo survey of 10,000+ Indian businesses (a vendor survey, 14 July 2026) found 42% had already left a provider over compliance.</p></section>',
        '<section class="card"><h2>Priya\'s week today, and with ' + e(NAME) + '</h2><div class="table-wrap"><table><thead><tr><th>Moment</th><th>Today</th><th>With the agent</th></tr></thead><tbody>' + today_rows + '</tbody></table></div><p class="small muted" style="margin:0">A normal morning has none to two items; the demo packs twelve into one day.</p></section>',
        '<div class="grid-2"><section class="card"><h2>Rules and AI</h2><div class="table-wrap"><table><thead><tr><th>Job</th><th>Who</th><th>Why</th></tr></thead><tbody>' + split_rows + '</tbody></table></div><p class="small muted" style="margin:0">Razorpay\'s own risk agent, Bumblebee, works the same way: deterministic rules first, the model only for interpretive tasks (Razorpay engineering blog, 2 Dec 2025).</p></section>',
        '<section class="card"><h2>What it reads</h2><div class="table-wrap"><table><thead><tr><th>Source</th><th>What</th><th>Access</th></tr></thead><tbody>' + read_rows + '</tbody></table></div><p class="small muted" style="margin:0">The model never sees card numbers or bank statements; client emails are read only in reply to approved notes.</p></section></div>',
        '<section class="card"><h2>The rules it works to</h2><div class="table-wrap"><table><thead><tr><th>Rule</th><th>Source</th></tr></thead><tbody>' + clock_rows + "</tbody></table></div></section>",
        '<section class="card"><h2>When things go wrong</h2><div class="table-wrap"><table><thead><tr><th>Situation</th><th>What the agent does</th></tr></thead><tbody>' + fail_rows + "</tbody></table></div></section>",
        '<section class="card"><h2>Where it would live in Razorpay</h2><ul><li>A new agent in <b>Agent Studio</b>, which today has no cross-border agent.</li><li>Its list shows inside <b>Exporter Dashboard 2.0</b>, which tracks payments but does not act on them.</li><li>It builds on what exists: MoneySaver global accounts, Payment Links, invoice upload, Apple Pay and Google Pay, and free FIRAs.</li><li>Morning summaries could reach the owner on WhatsApp through RAY, Razorpay\'s AI account manager (not built here).</li><li>Unpaid-invoice reminders stay with the RazorpayX Receivables Agent; disputes stay with Razorpay\'s dispute tools.</li><li>RAY already sends a link when a payment fails and answers when asked; Homeward asks why it failed first, and works the list every morning before anyone asks (the full comparison is on <a href="judges.html">For judges</a>).</li><li>First to ship: the morning list with declines and stuck money for every exporter; the EDF pack first for accounts whose bank needs the number before capture.</li></ul></section>',
        '<section class="card"><h2>Why it matters, in rupees</h2><p>Razorpay does not publish its cross-border volume, so this is a transparent model, not a measurement. Every input is sourced or labelled as an assumption; a pilot replaces the assumptions.</p><div class="table-wrap"><table><thead><tr><th>Input or result</th><th class="num">Low</th><th class="num">Base</th><th class="num">High</th><th>Source</th></tr></thead><tbody>' + sizing_rows + "</tbody></table></div>",
        "<p><b>For the merchant (base):</b> about 2.6% of overseas income comes back faster and more surely, and ₹2.64 lakh a year stops waiting about 10 days. <b>For Razorpay:</b> the fee on money won back is small (₹924 per exporter); the prize is keeping the exporter, worth about ₹35,200 a year in list fees, in a market where cheaper rivals sell \"we don't hold your money\". Across 1,000 exporters the base case is about ₹4.6 crore a year won back; each 1% of Razorpay's 100,000 exporters kept is worth about ₹3.5 crore a year. One decision costs Razorpay something on purpose: a declined card rerouted to a bank transfer earns 1% instead of 3%, and the merchant's ceiling is the ceiling; the volume and the exporter stay on Razorpay.</p></section>",
        '<section class="card"><h2>What is real and what is made up</h2><ul><li><b>Real:</b> the rules and their sources, Razorpay\'s products and fees, the public merchant quotes, and the blind test method and its results on the published test sets.</li><li><b>Made up:</b> Priya, her studio, every client, invoice, email and amount, the learning history, and every step marked "simulated".</li><li><b>Not built:</b> connections to Razorpay, banks, Zoho or email; live AI calls (the AI outputs shown were produced with Claude during the build and stored).</li><li><b>Not tested:</b> real bank narrations, real email threads, real decline messages; the pilot does that.</li></ul></section>',
    ])
    write("how-it-works.html", layout("how-it-works.html", "How it works", "The invoice journey, what merchants say, Priya's week today and with the agent, rules and AI, the rules it follows, failure cases and the rupee case.", body))


def page_judges():
    t = D["totals"]
    qs = [
        ("What data or signal identifies the opportunity",
         "Razorpay's own payment states: card declines with their reason text; cards authorised but not captured, with the 3-day refund clock; MoneySaver transfers waiting for an invoice or buyer details; review holds; replies to the agent's notes. Plus the merchant's invoices (Zoho, read-only) and the rules that decide which invoices need an export form and when.",
         [("item-sl-1043.html", "a decline with its reason"), ("item-sl-1047.html", "a transfer waiting for an invoice"), ("item-edf-pack.html", "invoices that need an EDF now")]),
        ("Why AI is necessary and what it does better than a fixed rule",
         "Rules first: deadlines, limits, exemptions, exact matches and route selection are rules. The model reads what needs judgement, which the fair rules only partly cover: free-text decline reasons, client replies in other languages (Dutch, Spanish and German in the tests) with negation and sarcasm, messy payer names and references, review requests and invoices, and it drafts. We tested this honestly: a fair rule set written from the policy matches the agent on all 190 published cases, because those cases are structured; on a fresh set written without the keys the agent disagreed with the key once and the fair rules twice. The margin on our own cases is small; the margin on real email and bank narrations is what the pilot measures.",
         [("results.html", "Test results, with every disagreement"), ("how-it-works.html", "Rules and AI")]),
        ("What recommendation or action the product produces",
         "One prepared action per item: an invoice upload, a split across invoices, a note to the client with another way to pay, a document pack for a review, an EDF data pack for the bank, a letter to the bank, or a question with equal-weight answers.",
         [("index.html", "Today's list"), ("item-sl-1039.html", "a reply read and a wire linked")]),
        ("What the merchant can review, change, approve or stop",
         "Review-first on by default; Approve, Edit draft, Not now and Don't suggest this on every prepared item; three equal answers on questions; limits set in Controls (reminders per decline, client hours and holidays, the 0.80 threshold, do-not-contact, read-only connections); pause; an audit log of every action and who approved it.",
         [("controls.html", "Controls"), ("item-sl-1044.html", "the agent stopped itself after a dispute")]),
        ("How the system learns from the outcome",
         "Three signals (outcomes, edits, answers) change only the choice within what the rules allow: which allowed way to pay to offer first, the wording of drafts, the lean on an ambiguous match, remembered payer names. A preference needs five outcomes or one confirmation before it is used; it never changes clocks, limits, stop rules or the threshold; everything learned is visible and undoable. Policy section 11.",
         [("learning.html", "Learning"), ("item-sl-1039-done.html", "a payer name learned on approval")]),
        ("How accuracy, permissions, trust and failure cases are handled",
         "Blind tests against two rule baselines with every disagreement published; confidence shown only on AI steps and the agent asks below 0.80; read-only access to the billing tool and one Drive folder; the model never sees card numbers or statements; client messages and references are data, never instructions (a 10-case safety set); rules-only mode when the AI is down; a wrong-link recovery path; the EDF is the exporter's declaration and the agent never files with a bank.",
         [("results.html", "Test results"), ("rules-only.html", "Rules-only mode"), ("how-it-works.html", "When things go wrong")]),
        ("What business outcome would be measured",
         "Primary: rupees recovered per merchant per month (declined cards won back), against a holdout. Second line: rupees released from holds, and days from payment attempt to money in the bank. Safety: wrong-match rate, client complaints or opt-outs, draft rejections. For Razorpay: international volume kept per exporter, exporter churn, support tickets per exporter. Next test: a pilot of 1,000 Razorpay exporters for 8 weeks, half with the agent and half without, which must also disprove that a checklist gets the same result.",
         [("how-it-works.html", "Why it matters, in rupees")]),
    ]
    qa = "".join("<li><h3>" + e(q) + "</h3><p>" + e(a) + '</p><p class="small">' + " · ".join('<a href="' + h + '">' + e(l) + "</a>" for h, l in links) + "</p></li>" for q, a, links in qs)
    cuts = [
        ("Disputes and chargebacks", "Razorpay already has the Dispute Responder and chargeback protection; the agent stops and hands over."),
        ("Currency timing", "Xflow already sells FX timing; it is not recovery."),
        ("Goods exporters", "Their EDF goes through customs with the shipping bill."),
        ("Payouts from Amazon, Upwork and Freelancer", "Razorpay does not ask for invoices for them."),
        ("Filing with the bank", "The bank is the authority; the agent prepares, the owner submits."),
        ("Sending without approval", "Trust, and Agent Studio's own principle that no irreversible action happens without explicit approval."),
        ("General unpaid-invoice reminders", "RazorpayX's Receivables Agent already chases unpaid invoices; Homeward acts only when a payment has failed or money is stuck."),
        ("Large firms with treasury teams", "Different needs; small teams feel the pain most."),
        ("A live integration in the prototype", "Three weeks went on a rulebook, a blind test and a static site every reader can open, rather than a brittle Zoho or email connection; the judgement, not the plumbing, is what this entry shows."),
    ]
    cut_rows = "".join('<li><b>' + e(a) + "</b><span>" + e(b) + "</span></li>" for a, b in cuts)
    assumptions = ["Decline rates and reasons on exporter accounts", "Share and length of payments waiting for documents, and how many end in automatic refunds", "Share of MoneySaver users whose bank needs an EDF number before capture", "How often a client pays another way after a decline, and the recovery rate by route", "How many drafts the owner approves, edits or rejects", "Real bank narrations and email threads: where the model's margin over rules actually is"]
    body = "".join([
        "<h1>For judges</h1>",
        '<p class="lede">The brief\'s seven questions, answered in its own words with links to where each is shown; what was deliberately left out; what is measured; what is real. The one-page note, the video and the AI build log are the submission; this page is the map of the prototype.</p>',
        '<section class="card"><h2>The problem in one paragraph</h2><p>Small Indian services firms (agencies, SaaS firms, small IT shops) earn in dollars but cannot always touch the money. Foreign cards get declined and nobody tells the client another way to pay; transfers arrive and sit uncaptured until an invoice is matched by hand; from 1 October 2026 every services invoice needs an export declaration, and some banks need the form\'s number before the money can be captured at all. Razorpay\'s Exporter Dashboard shows these states and its invoice-upload and pending-action flows ask the merchant to act; nothing today works out the fix across declines, matching and export forms and prepares it for one approval. ' + e(NAME) + ' treats the invoice as the unit of work and, each morning, lists the money that is not home, says why, and prepares the fix for the owner to approve. In the demo morning that is ' + inr_short(t["not_home_inr"]) + ' across ' + str(t["count"]) + " items (synthetic).</p></section>",
        '<section class="card"><h2>The seven questions</h2><ol class="qa">' + qa + "</ol></section>",
        '<section class="card"><h2>What was deliberately left out, and why</h2><ul class="kv">' + cut_rows + "</ul></section>",
        '<section class="card"><h2>What Razorpay already does, and where Homeward starts</h2><div class="table-wrap"><table><thead><tr><th>Razorpay today</th><th>What it does</th><th>Where Homeward starts</th><th>Source</th></tr></thead><tbody><tr><td><b>RAY on WhatsApp</b></td><td>Sends payment links to customers whose payments failed that day; offers payment rerouting; summaries and settlement warnings</td><td>A new link to a card the issuer blocked for cross-border risk fails again. Homeward reads the decline reason and the client\'s history, offers a rail that can succeed, writes in the owner\'s voice at the client\'s 9 am, and keeps the invoice open until the money is in the bank</td><td class="small muted">Razorpay blog and PR, 2 Sep 2026</td></tr><tr><td><b>Agentic Dashboard</b></td><td>Reconciles from a bank-statement screenshot; reads a complaint screenshot, gives the decline reason and suggests a payment link; standing rules for future failed transactions</td><td>Works on request, from a screenshot. Homeward runs every morning over the invoices, splits one transfer across invoices, tolerates a bank charge, and the match leads straight to the capture and the export form</td><td class="small muted">Razorpay blog, 12 Mar 2026</td></tr><tr><td><b>RazorpayX Receivables Agent</b></td><td>Follows up unpaid invoices and sends reminders</td><td>Homeward never sends a general reminder; it acts only when a payment failed, arrived but is stuck, or a form blocks it</td><td class="small muted">Razorpay PR, 1 Jun 2026</td></tr><tr><td><b>Exporter Dashboard 2.0</b></td><td>Global account details, one-click invoice upload, savings calculator, live tracking</td><td>Shows the states; Homeward lives inside it and prepares the fix for each one</td><td class="small muted">Razorpay Sprint page, 2026</td></tr><tr><td><b>MoneySaver invoice upload</b></td><td>A bank transfer is captured only after the merchant uploads the matching invoice and buyer details</td><td>The upload exists; finding which invoice, the split, the charge tolerance and the part payment are the work Homeward does</td><td class="small muted">Razorpay docs</td></tr><tr><td><b>Smart Collect 2.0</b></td><td>Virtual account numbers match each domestic bank transfer to its payer</td><td>Overseas clients pay by SWIFT and card with free-text references and no virtual account per payer; the match needs reading, not an identifier</td><td class="small muted">Razorpay blog, 20 Feb 2025</td></tr><tr><td><b>Optimizer and Vulcan</b></td><td>Routing and fraud models that raise success rates before the decline</td><td>They prevent declines; Homeward handles the ones that still happen and the issuer\'s no</td><td class="small muted">Razorpay docs; PR, 18 Aug 2026</td></tr><tr><td><b>Agent Studio catalogue</b></td><td>26 agents across e-commerce, lending, investments and insurance; none for cross-border payments, exporters, export forms or invoice matching</td><td>Homeward is the Studio\'s own pattern (review first, logged, approval before contact) applied to the segment the catalogue skips</td><td class="small muted">razorpay.com/agent-studio, read 13 Oct 2026</td></tr><tr><td><b>EDF help</b></td><td>"Reach out to our cross-border support team"; Razorpay is working with the bank on EDF generation</td><td>The form is one of six stages; Homeward does the other five and the join between them</td><td class="small muted">Razorpay blog, 8 Oct 2026; 21 Sep 2026</td></tr></tbody></table></div><p class="small muted">Checked against Razorpay\'s own pages and posts; dates are the posts\' dates. The platform rules Homeward runs under (approval before contact, review-first mode, an instant off switch, a full log, consent and permanent opt-outs) are Agent Studio\'s own (Razorpay blog, 30 Mar 2026).</p></section>',
        '<section class="card"><h2>Why now, and why Razorpay</h2><ul><li>The EDF regime began on 1 October 2026 and the regulation was amended on 22 September; Razorpay\'s own help for it is "reach out to our cross-border support team".</li><li>Razorpay\'s cross-border business grows 40% a year and was loss-making in October 2025; rivals sell "we don\'t hold your money" and EDF tools.</li><li>Agent Studio has no cross-border agent; Exporter Dashboard 2.0 tracks but does not act; the Receivables Agent chases unpaid invoices, which Homeward leaves to it.</li><li>The guardrails here are Agent Studio\'s published principles, line by line: approval before irreversible action, the merchant\'s ceiling, a no is a no, a full audit trail, review-first, no dark patterns.</li></ul></section>',
        '<section class="card"><h2>Assumptions to validate with Razorpay data in the pilot</h2><ul>' + "".join("<li>" + e(a) + "</li>" for a in assumptions) + "</ul></section>",
        '<section class="card"><h2>What is real, made up, not built and not tested</h2><ul><li><b>Real:</b> the rules and their sources (re-read 12 October 2026), Razorpay\'s products and list fees, the public merchant quotes, the test method and its results on the published sets.</li><li><b>Made up:</b> the merchant, clients, invoices, emails, amounts and the learning history.</li><li><b>Not built:</b> connections to Razorpay, banks, Zoho or email; live AI calls; the AI outputs shown were produced during the build and stored.</li><li><b>Not tested:</b> real bank feeds, real email, real decline text; no merchant was interviewed.</li></ul></section>',
        '<section class="card"><h2>Reading order for a short visit</h2><ol><li><a href="index.html">Today</a>: the money and the list.</li><li><a href="item-sl-1039.html">Copperline</a>: a reply read, reminders stopped, a wire linked.</li><li><a href="item-sl-1043.html">Larkspur</a>: a decline rerouted, a note drafted.</li><li><a href="item-sl-1052-1053.html">Tidewater</a>: the agent won\'t guess.</li><li><a href="controls.html">Controls</a> and <a href="results.html">Test results</a>.</li></ol></section>',
    ])
    write("judges.html", layout("judges.html", "For judges", "The brief's seven questions answered with links, what was left out and why, what is measured, and what is real.", body))


def llms_txt():
    t = D["totals"]
    lines = [
        "# " + NAME + ": " + TAGLINE,
        "",
        "Concept prototype by " + AUTHOR + " for the Razorpay AI x PM Build Challenge at ISB (October 2026), Track 2, Recover and Grow with AI. Not a Razorpay product. All merchant data is synthetic.",
        "",
        "## What it is",
        "An agent, imagined inside Razorpay's Agent Studio and shown in the Exporter Dashboard, for small Indian services firms paid by overseas clients through Razorpay. The unit of work is the invoice: an invoice is done only when it is Sent, Paid, Linked, Declared (where required), In bank and Closed. Each morning the agent lists the money that is not home, says why, and prepares the fix. The owner approves, edits or stops each step.",
        "",
        "## Three areas, one engine",
        "1. Declined international card payments: the agent classifies the decline, a rule picks the next way to pay (local bank transfer, wallet, retry with the right address), and the agent drafts a short note.",
        "2. Money that arrived but is stuck: links payments to invoices when the payer, amount or reference differs; splits one transfer across invoices; records bank charges and part payments; prepares document packs for reviews.",
        "3. Export declaration forms (EDF, RBI FEMA 23(R)/2026-RB, in force 1 Oct 2026, amended 22 Sep 2026): which invoices need one and when, the data pack, purpose-code checks, the ₹10 lakh declaration route, the nine-month realisation deadline, and the bank-specific rule (ICICI) that needs an EDF number before capture.",
        "",
        "## The seven questions",
        "Signal: Razorpay payment states (decline reasons, authorised-not-captured with the 3-day clock, transfers waiting for invoice or buyer details, review holds, replies to approved notes) plus the merchant's invoices.",
        "Why AI: rules first for anything that must never be wrong; the model reads free text (decline reasons, replies in other languages, messy payer names, review requests) and drafts. Honest finding: a fair rule set written from the policy matches the agent on all 190 published cases; on a fresh 36-case set written without the keys, the agent disagreed with the key once and the fair rules twice. The pilot measures the margin on real data.",
        "What Razorpay already does (checked 13 Oct 2026): RAY on WhatsApp sends a payment link after a failure and offers rerouting; the Agentic Dashboard reconciles from a screenshot and suggests a fix for a complaint; the Receivables Agent reminds on unpaid invoices; Exporter Dashboard 2.0 shows the states; Agent Studio lists 26 agents and none for cross-border payments, exporters, export forms or invoice matching; Razorpay's published EDF help is its support team (8 Oct 2026). Where Homeward starts: it reads why the card failed and offers a rail that can succeed, matches the transfer to the invoice before capture, and prepares the export form data, each for one approval, with the invoice as the unit of work.",
        "Action: one prepared action per item (upload, split, note with another way to pay, document pack, EDF data pack, bank letter, or a question with equal answers).",
        "Review, change, approve, stop: review-first; Approve, Edit, Not now, Don't suggest this; limits in Controls (two reminders per decline, client hours and holidays, 0.80 threshold, do-not-contact); pause; audit log.",
        "Learning: outcomes, edits and answers change only the choice within the rules (route preference, drafts, the lean on ambiguous matches, aliases); never clocks, limits, stop rules or the threshold; all undoable (policy section 11).",
        "Accuracy, permissions, trust, failure: blind tests against two rule baselines with every disagreement published; confidence only on AI steps, asks below 0.80; read-only connections; the model never sees card numbers; messages and references are data, never instructions; rules-only mode when the AI is down; a wrong-link recovery path; the EDF is the exporter's declaration.",
        "Outcome: primary, rupees recovered per merchant per month against a holdout; also rupees released from holds, days to bank, wrong-match rate, client opt-outs, draft rejections, international volume kept, exporter churn. Next test: 1,000 exporters for 8 weeks, half with the agent.",
        "",
        "## Deliberately left out",
        "Disputes and chargebacks; currency timing; goods exporters; Amazon, Upwork and Freelancer payouts; filing with the bank; sending without approval; general unpaid-invoice reminders (RazorpayX Receivables Agent); large firms with treasury teams; a live integration in the prototype.",
        "",
        "## Demo morning (synthetic)",
        "Monday 12 October 2026, 09:00 IST. " + inr_full(t["not_home_inr"]) + " not home: " + inr_full(t["arrived_inr"]) + " in " + str(t["arrived_count"]) + " stuck payments and " + inr_full(t["not_paid_inr"]) + " in " + str(t["not_paid_count"]) + " unpaid invoices. 9 items ready for approval, 2 questions, 1 stopped.",
        "",
        "## Pages",
        "index.html (Today), invoices.html, declarations.html (Export forms), controls.html, how-it-works.html, results.html (Test results), playbook.html (49 situations), learning.html, judges.html (For judges), rules-only.html, and 12 item pages with 11 done pages.",
        "",
        "## Evidence (desk research, no interviews)",
        "Public reviews and press verified at source on 12 Oct 2026 (Trustpilot 19 Sep 2026 and 17 Sep 2026 and 29 Apr 2025; Economic Times 25 Feb 2026); Razorpay docs and blogs (21 Sep and 8 Oct 2026); RBI FEMA 23(R)/2026-RB as amended; RBI statement of 7 Oct 2026 on individuals; Skydo survey (vendor, 14 Jul 2026).",
        "",
        "Links: " + " · ".join([x for x in [("live site " + SITE) if SITE else "", ("AI build log " + LOG) if LOG else "", ("code, policy and test sets " + REPO) if REPO else "", ("agent policy " + CFG.get("policy_url", "")) if CFG.get("policy_url") else ""] if x]),
    ]
    (DOCS / "llms.txt").write_text("\n".join(lines) + "\n")


def preview_svg():
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 630' width='1200' height='630'>"
           "<rect width='1200' height='630' fill='#f6f7f9'/>"
           "<circle cx='120' cy='120' r='40' fill='none' stroke='#15325b' stroke-width='10'/><circle cx='120' cy='120' r='16' fill='#0f7b5f'/>"
           "<text x='190' y='138' font-family='IBM Plex Sans, system-ui, sans-serif' font-size='56' font-weight='600' fill='#0f1b2d'>" + NAME + "</text>"
           "<text x='80' y='260' font-family='IBM Plex Sans, system-ui, sans-serif' font-size='40' fill='#3b4a5f'>" + TAGLINE + "</text>"
           "<text x='80' y='340' font-family='IBM Plex Sans, system-ui, sans-serif' font-size='28' fill='#64748b'>An agent for small Indian services exporters on Razorpay.</text>"
           "<text x='80' y='385' font-family='IBM Plex Sans, system-ui, sans-serif' font-size='28' fill='#64748b'>Rules first, AI for judgement, the owner approves.</text>"
           "<g transform='translate(80 470)'>"
           + "".join("<circle cx='" + str(i * 180 + 20) + "' cy='20' r='14' fill='" + ("#0f7b5f" if i < 2 else "#ffffff") + "' stroke='" + ("#0f7b5f" if i < 2 else "#b42318" if i == 2 else "#dde3ea") + "' stroke-width='4'/>" for i in range(6))
           + "".join("<rect x='" + str(i * 180 + 34) + "' y='18' width='152' height='4' fill='" + ("#0f7b5f" if i < 1 else "#dde3ea") + "'/>" for i in range(5))
           + "".join("<text x='" + str(i * 180 + 20) + "' y='70' text-anchor='middle' font-family='IBM Plex Sans, system-ui, sans-serif' font-size='22' fill='#64748b'>" + s + "</text>" for i, s in enumerate(STAGES))
           + "</g>"
           "<text x='80' y='600' font-family='IBM Plex Sans, system-ui, sans-serif' font-size='20' fill='#64748b'>Concept prototype for the Razorpay AI x PM Build Challenge, ISB 2026. Not a Razorpay product. All data is made up.</text>"
           "</svg>")
    (DOCS / "assets" / "preview.svg").write_text(svg)


def downloads():
    dl = DOCS / "downloads"
    dl.mkdir(exist_ok=True)
    header = ["note", "invoice_no", "invoice_date", "client", "client_country", "service", "currency", "invoice_amount",
              "amount_received", "received_on", "payment_reference", "purpose_code", "purpose_code_question", "route"]
    pack = [
        ["Illustrative prototype data. Confirm fields against your bank's EDF format.", "SL-1045", "2026-10-03", "Juniper Ridge Inc", "CA", "Product design sprint 2", "USD", "2400.00", "2400.00 (part of 5400.00 with SL-1040)", "2026-10-07", "SL1040/1045", "", "Left blank: design work, confirm P0802 or P0806 with the bank before filing", "Self-declaration (under INR 10 lakh)"],
        ["", "SL-1047", "2026-10-05", "Larkspur Labs Inc", "US", "Website build, sprint 2", "USD", "2000.00", "1950.00 (50.00 bank charges)", "2026-10-09", "INV1047 OCT", "P0802", "", "Self-declaration (under INR 10 lakh); shortfall by declaration"],
        ["", "SL-1054", "2026-10-06", "Fernhill Analytics Ltd", "GB", "Data product design: discovery", "GBP", "3200.00", "3200.00", "2026-10-09", "SL-1054", "", "Left blank: design work, confirm P0802 or P0806 with the bank before filing", "Self-declaration (under INR 10 lakh)"],
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(pack)
    (dl / "edf-pack-sl-1045-1047-1054.csv").write_text(buf.getvalue())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["note", "invoice_no", "client", "client_country", "service", "currency", "invoice_amount", "payment_status", "when_to_file", "purpose_code_check"])
    for i, r in enumerate(D["edf_october"]):
        w.writerow(["Illustrative prototype data." if i == 0 else "", r["invoice"], r["client"], r["country"], r["service"], r["ccy"], format(r["amount"], ".2f"), r["payment"], r["when"], r["code"]])
    (dl / "edf-october-2026.csv").write_text(buf.getvalue())
    letter = BY_SLUG["sl-0981"]
    (dl / "extension-request-sl-0981.txt").write_text(
        "Illustrative prototype letter. All names and amounts are made up.\n\n"
        "To: ICICI Bank, trade desk\nSubject: " + letter["draft_subject"] + "\n\n" + "\n\n".join(letter["draft"]) + "\n")


def main():
    DOCS.mkdir(exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    page_today()
    for it in ITEMS:
        item_page(it)
    page_invoices()
    page_declarations()
    page_playbook()
    page_results()
    page_learning()
    page_controls()
    page_rules_only()
    page_how()
    page_judges()
    llms_txt()
    preview_svg()
    downloads()
    for src, dst in ((ROOT / "BUILD_LOG.md", DOCS / "BUILD_LOG.md"), (ROOT / "agent" / "policy.md", DOCS / "policy.md")):
        if src.exists():
            dst.write_text(src.read_text())
    print("pages:", len(list(DOCS.glob("*.html"))))


if __name__ == "__main__":
    main()
