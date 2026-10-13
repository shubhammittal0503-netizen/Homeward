"""Homeward demo data: one illustrative merchant, her overseas invoices and every item the agent prepared on
the morning of Monday 12 October 2026. All names, companies, emails and amounts are made up.

Writes data/demo.json, which tools/build_site.py renders into the site.
Standard library only. Run: python3 tools/demo_data.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FX = {"USD": 88.0, "GBP": 117.0, "EUR": 102.0}  # illustrative rates, not live
SYM = {"USD": "$", "GBP": "£", "EUR": "€"}


def inr(ccy, amt):
    return round(amt * FX[ccy])


MERCHANT = {
    "owner": "Priya",
    "business": "Saffron Loop Studio LLP",
    "city": "Pune",
    "what": "A design and product studio with clients in the US, UK, Europe, Singapore, Australia and Canada",
    "entity": "LLP (a firm, so the export declaration form applies)",
    "settles_to": "ICICI Bank",
    "accounts": "Razorpay MoneySaver global accounts in USD, GBP and EUR; international cards switched on",
    "purpose_code": "P0802, Software consultancy or implementation (chosen when the account was activated)",
    "billing": "Zoho Books, read-only",
    "contracts": "Google Drive folder \"Contracts\", read-only, used only when Priya approves a pack",
}

STAGES = ["Sent", "Paid", "Linked", "Declared", "In bank", "Closed"]

# Journey states per stage: done, stuck, todo, na (not needed), wait
ITEMS = [
    # 1. Card payment authorised, waiting for its invoice, about to refund
    {
        "slug": "sl-1051", "approved_at": "09:03", "journey_after": ["done", "done", "done", "todo", "wait", "todo"], "invoices": ["SL-1051"], "client": "Bramble & Finch Ltd", "country": "UK",
        "ccy": "GBP", "amount": 1800.0, "bucket": "prepared", "rank": 1, "kind": "Waiting for an invoice",
        "title": "Capture Bramble & Finch's £1,800 before it refunds",
        "line": "A card payment is waiting for its invoice. It refunds automatically tomorrow at 10:42.",
        "why_now": "Razorpay refunds a card payment that is not captured within 3 days of its creation. Oliver paid on Saturday 10 October at 10:42.",
        "urgency": "Refunds in 1 day", "urgency_level": "high",
        "journey": ["done", "done", "stuck", "todo", "todo", "todo"],
        "facts": [
            ("Sat 10 Oct, 10:42 IST: Oliver Grant paid invoice SL-1051 (£1,800) by Mastercard. Status: authorised, waiting for an invoice.", "Razorpay payment record"),
            ("Invoice SL-1051, UX research and design, £1,800, dated 7 Oct 2026, is in Zoho Books.", "Zoho Books"),
            ("Razorpay captures international payments only with an invoice, and refunds card payments not captured within 3 days of creation.", "Razorpay docs"),
        ],
        "steps": [
            ("Rule", "Exact match: same client, same amount, and the payment description says SL-1051.", None),
            ("Rule", "Clock: 1 day left before the automatic refund (Tue 13 Oct, 10:42).", None),
            ("Rule", "Invoice dated 7 Oct and you are an LLP, so it goes in October's export form, due 30 Nov. Razorpay's blog ties the EDF-number-before-capture rule to MoneySaver payments, so this card payment can be captured now.", None),
        ],
        "baseline": "A fixed rule also finds this one. What it lacks is the clock: nothing tells you it refunds tomorrow.",
        "prepared": ["Upload invoice SL-1051 to the payment, so Razorpay can capture it."],
        "limits": ["Nothing goes to the client.", "Only the invoice already in Zoho is uploaded."],
        "approve_label": "Approve upload",
        "after": [
            ("09:03", "Invoice SL-1051 uploaded to the payment.", False),
            ("09:04", "Payment captured. The automatic refund is cancelled.", True),
            ("Next cycle", "Settles to ICICI on Razorpay's international card settlement cycle.", True),
            ("Within 24 hours of settlement", "FIRA arrives by email (Razorpay issues it free).", True),
            ("By 30 Nov", "SL-1051 joins October's export form.", False),
        ],
        "audit": "Uploaded invoice SL-1051 to payment of £1,800. Approved by Priya.",
    },
    # 2. Nine-month realisation deadline
    {
        "slug": "sl-0981", "approved_at": "09:05", "journey_after": ["done", "wait", "todo", "na", "todo", "todo"], "invoices": ["SL-0981"], "client": "Copperline Studios Pty Ltd", "country": "Australia",
        "ccy": "USD", "amount": 1200.0, "bucket": "prepared", "rank": 2, "kind": "Deadline",
        "title": "SL-0981 reaches its nine-month limit on 20 October",
        "line": "Put the delay on record with ICICI before the limit passes. The letter is ready.",
        "why_now": "Export money is due within nine months of the invoice date, and an exporter still unpaid a year past that can be restricted to advance payment only. SL-0981 is dated 20 January 2026, so the limit is 20 October 2026.",
        "urgency": "8 days left", "urgency_level": "high",
        "journey": ["done", "stuck", "todo", "na", "todo", "todo"],
        "facts": [
            ("Invoice SL-0981, pitch deck design, $1,200, dated 20 Jan 2026, is still unpaid.", "Zoho Books"),
            ("On 30 Sep, Copperline's accounts team wrote that it is scheduled for their November payment run.", "Inbox"),
            ("RBI: export proceeds are due within nine months; the bank can extend the time when the exporter asks with reasons. Unpaid a year past the due date, the exporter may only export against advance payment or a letter of credit.", "RBI FEMA 23(R)/2026-RB, Regulations 5 and 13"),
            ("The invoice predates the 1 October export-form regime, so ICICI holds no declaration for it. The letter asks the bank to record the expected date, so the money can be received and matched without question when it arrives.", "Agent note"),
        ],
        "steps": [
            ("Rule", "Clock: 8 days to the nine-month limit.", None),
            ("Rule", "Reminding Copperline to pay is the RazorpayX Receivables Agent's job, so Homeward does not chase them. Homeward handles the bank side.", None),
            ("AI", "Drafted a request to ICICI to record an extension to 31 Dec 2026, using the reason in Copperline's email of 30 Sep.", 0.93),
        ],
        "baseline": "A fixed rule can flag the date. It cannot find the reason in the client's email or write the request.",
        "prepared": ["Extension request letter to ICICI's trade desk, with Copperline's email of 30 Sep attached. You decide whether to send it; some banks will only note it."],
        "draft_kind": "Letter to ICICI Bank, trade desk",
        "draft_subject": "Request to extend the realisation period for export invoice SL-0981",
        "draft": [
            "Dear Sir or Madam,",
            "Saffron Loop Studio LLP requests an extension of the period for realising the export value of invoice SL-0981 (USD 1,200, dated 20 January 2026, client Copperline Studios Pty Ltd, Australia).",
            "Reason: the client has confirmed that the payment is scheduled in its November 2026 payment run (email of 30 September 2026, attached).",
            "We request an extension to 31 December 2026.",
            "Priya, Designated Partner, Saffron Loop Studio LLP",
        ],
        "limits": ["You send the letter to ICICI; the agent does not file anything with the bank.", "No message goes to Copperline."],
        "approve_label": "Approve and download letter",
        "after": [
            ("09:05", "Letter downloaded for you to send to ICICI's trade desk.", False),
            ("Thu 15 Oct", "If ICICI has not replied, the agent reminds you.", False),
            ("20 Oct", "Deadline. The agent shows the extension status here.", False),
        ],
        "download": "extension-request-sl-0981.txt",
        "audit": "Prepared an extension request for SL-0981. Downloaded by Priya.",
    },
    # 3. EDF pack needed before capture (ICICI)
    {
        "slug": "edf-pack", "approved_at": "09:20", "journey_after": ["done", "done", "done", "wait", "todo", "todo"], "invoices": ["SL-1045", "SL-1047", "SL-1054"], "client": "3 clients", "country": "",
        "ccy": None, "amount": None, "bucket": "prepared", "rank": 3, "kind": "Export form",
        "title": "Export forms for 3 invoices, to release ₹10.2 lakh",
        "line": "Your account settles to ICICI, so Razorpay needs an EDF number before it captures these payments.",
        "why_now": "Three bank transfers have arrived for invoices dated after 1 October. Razorpay cannot capture them until ICICI gives an EDF number.",
        "urgency": "Blocks ₹10.2 lakh", "urgency_level": "high",
        "journey": ["done", "done", "done", "stuck", "todo", "todo"],
        "facts": [
            ("Your firm is an LLP. RBI said on 7 Oct that individuals on personal-nature contracts need not report; firms still file the EDF.", "RBI via Business Today, 7 Oct 2026"),
            ("Services invoices dated on or after 1 Oct 2026 need an EDF within 30 days of the month's end; one EDF can cover a month.", "RBI FEMA 23(R)/2026-RB, Regulation 3(2)"),
            ("For accounts settling to ICICI: \"you will be required to file for EDF number before capturing any payment with Razorpay Moneysaver.\"", "Razorpay blog, 21 Sep 2026"),
            ("Waiting: $5,400 from Juniper Ridge (pays SL-1040 and SL-1045), $1,950 from Larkspur (SL-1047), £3,200 from Fernhill (SL-1054).", "Razorpay MoneySaver"),
        ],
        "steps": [
            ("Rule", "Which invoices need an EDF now: dated on or after 1 Oct, with money already waiting. SL-1045, SL-1047 and SL-1054. SL-1040 is dated 30 Sep, so it needs none.", None),
            ("AI", "Read each invoice and filled the fields the bank asks for: invoice number and date, client and country, service, currency and amount, and the payment received.", 0.95),
            ("Rule", "Each invoice is under ₹10 lakh, so a self-declaration of the payment can close it with the bank.", None),
            ("AI", "Purpose code check: SL-1045 and SL-1054 are design work, and your account's code is P0802, Software consultancy or implementation. Sources disagree on the code for design work, so the agent asks rather than guesses.", 0.62),
        ],
        "baseline": "A fixed rule can list invoices by date. It cannot read the service on each invoice, notice that the code may not fit, or know which payments are blocked.",
        "prepared": [
            "EDF data for SL-1045, SL-1047 and SL-1054, ready to download for ICICI.",
            "A question for you: confirm the purpose code for the two design invoices with ICICI or your CA.",
        ],
        "limits": ["You submit the EDF to ICICI; the agent never files with the bank.", "The purpose code is your decision."],
        "approve_label": "Approve and download the pack",
        "after": [
            ("09:20", "EDF pack downloaded. You submit it through ICICI Trade Online or your branch.", False),
            ("Each morning", "The agent checks for EDF numbers and asks you to mark them received.", False),
            ("Once numbers arrive", "Razorpay captures the three payments within 60 minutes, then settles T+1.", True),
            ("T+1", "About ₹10.2 lakh (at ₹88, before fees) reaches your ICICI account. FIRA within 24 hours of settlement.", True),
        ],
        "download": "edf-pack-sl-1045-1047-1054.csv",
        "audit": "Prepared EDF data for SL-1045, SL-1047, SL-1054. Downloaded by Priya.",
    },
    # 4. Larkspur parent company short payment
    {
        "slug": "sl-1047", "approved_at": "09:08", "journey_after": ["done", "done", "done", "wait", "todo", "todo"], "invoices": ["SL-1047"], "client": "Larkspur Labs Inc", "country": "US",
        "ccy": "USD", "amount": 1950.0, "bucket": "prepared", "rank": 4, "kind": "Waiting for an invoice",
        "title": "$1,950 from LARKSPUR HOLDINGS LLC is waiting for an invoice",
        "line": "Link it to SL-1047 and record $50 as bank charges.",
        "why_now": "The money arrived on 9 Oct. Razorpay will not settle it without an invoice and buyer details.",
        "urgency": "Arrived 3 days ago", "urgency_level": "medium",
        "journey": ["done", "done", "stuck", "todo", "todo", "todo"],
        "facts": [
            ("9 Oct: $1,950 by US bank transfer (ACH) from LARKSPUR HOLDINGS LLC, reference \"INV1047 OCT\". Status: waiting for invoice and buyer details.", "Razorpay MoneySaver"),
            ("Open for Larkspur Labs Inc: SL-1047, website build sprint 2, $2,000, dated 5 Oct; SL-1043, $2,400, card declined.", "Zoho Books"),
            ("You confirmed on 9 Sep that LARKSPUR HOLDINGS LLC is Larkspur Labs' parent company.", "Agent memory"),
        ],
        "steps": [
            ("AI", "Match: SL-1047. The reference contains 1047, the payer is Larkspur's known parent, and the $50 gap is a typical intermediary bank charge on a US transfer.", 0.94),
            ("Rule", "$50 is within the bank-charge limit (at most $50 and 3%), so it is recorded as a charge, not chased.", None),
            ("Rule", "The shortfall is under ₹10 lakh, so you can close the invoice by declaration to your bank.", None),
            ("Rule", "Dated 5 Oct, so an EDF is needed, and ICICI needs its number before capture. Added to today's export form pack.", None),
        ],
        "baseline": "A fixed rule finds no match: the payer is not the client's name and the amount is $50 short. The money stays stuck.",
        "prepared": [
            "Attach invoice SL-1047 and Larkspur's buyer details from Zoho.",
            "Record $50 as bank charges against SL-1047.",
            "Add SL-1047 to the export form pack.",
        ],
        "limits": ["Nothing goes to the client.", "If you pick a different invoice, the agent learns from it."],
        "approve_label": "Approve link",
        "after": [
            ("09:08", "Invoice SL-1047 and buyer details attached to the payment.", False),
            ("09:08", "$50 recorded as bank charges; the declaration is noted for month end.", False),
            ("After ICICI's EDF number", "Razorpay captures within 60 minutes and settles T+1.", True),
            ("T+1", "About ₹1,71,600 (at ₹88, before fees) reaches your ICICI account.", True),
        ],
        "audit": "Linked $1,950 from LARKSPUR HOLDINGS LLC to SL-1047; recorded $50 bank charges. Approved by Priya.",
    },
    # 5. Juniper one transfer for two invoices
    {
        "slug": "sl-1040-1045", "approved_at": "09:09", "journey_after": ["done", "done", "done", "wait", "todo", "todo"], "invoices": ["SL-1040", "SL-1045"], "client": "Juniper Ridge Inc", "country": "Canada",
        "ccy": "USD", "amount": 5400.0, "bucket": "prepared", "rank": 5, "kind": "Waiting for an invoice",
        "title": "$5,400 from Juniper Ridge pays two invoices",
        "line": "Split it across SL-1040 and SL-1045.",
        "why_now": "The money arrived on 7 Oct and is waiting for invoices.",
        "urgency": "Arrived 5 days ago", "urgency_level": "medium",
        "journey": ["done", "done", "stuck", "todo", "todo", "todo"],
        "facts": [
            ("7 Oct: $5,400 by ACH from JUNIPER RIDGE INC, reference \"SL1040/1045\". Waiting for invoices and buyer details.", "Razorpay MoneySaver"),
            ("Open: SL-1040, product design sprint 1, $3,000, dated 30 Sep; SL-1045, product design sprint 2, $2,400, dated 3 Oct.", "Zoho Books"),
        ],
        "steps": [
            ("AI", "Split: the reference names both invoices and $3,000 plus $2,400 is exactly $5,400.", 0.97),
            ("Rule", "SL-1040 is dated before 1 Oct, so it needs no EDF; SL-1045 needs one. The whole payment waits for SL-1045's EDF number (ICICI).", None),
        ],
        "baseline": "A fixed rule matches one invoice at a time. One payment for two invoices stays unmatched.",
        "prepared": ["Attach SL-1040 and SL-1045 and Juniper's buyer details.", "Add SL-1045 to the export form pack."],
        "limits": ["Nothing goes to the client."],
        "approve_label": "Approve split",
        "after": [
            ("09:09", "Both invoices attached to the payment.", False),
            ("After ICICI's EDF number for SL-1045", "Razorpay captures within 60 minutes and settles T+1.", True),
            ("T+1", "About ₹4,75,200 (at ₹88, before fees) reaches your ICICI account.", True),
        ],
        "audit": "Split $5,400 from JUNIPER RIDGE INC across SL-1040 and SL-1045. Approved by Priya.",
    },
    # 6. Fernhill review asking for documents
    {
        "slug": "sl-1054", "approved_at": "09:15", "journey_after": ["done", "done", "done", "wait", "wait", "todo"], "invoices": ["SL-1054"], "client": "Fernhill Analytics Ltd", "country": "UK",
        "ccy": "GBP", "amount": 3200.0, "bucket": "prepared", "rank": 6, "kind": "Under review",
        "title": "Razorpay's review team needs documents for Fernhill's £3,200",
        "line": "Pack ready: the invoice, the signed scope of work, proof of delivery. No client emails.",
        "why_now": "A first payment from a new client is under review. Settlement waits until the review clears.",
        "urgency": "Review open since 9 Oct", "urgency_level": "medium",
        "journey": ["done", "done", "done", "todo", "stuck", "todo"],
        "facts": [
            ("9 Oct: £3,200 by Faster Payments from FERNHILL ANALYTICS LTD, reference \"SL-1054\". Matched to SL-1054 by rule.", "Razorpay MoneySaver"),
            ("Razorpay's request (illustrative): \"Please share the contract or statement of work and proof of service delivery for this payment.\"", "Razorpay review"),
            ("Invoice SL-1054, data product design: discovery, £3,200, dated 6 Oct.", "Zoho Books"),
        ],
        "steps": [
            ("Rule", "Matched exactly to SL-1054 (reference and amount).", None),
            ("AI", "Read the request: it needs a contract or scope of work, and proof of delivery.", 0.96),
            ("AI", "Chose three documents: invoice SL-1054, the signed scope of work (Fernhill_SOW_signed.pdf) and the delivered discovery readout (Discovery_readout_v3.pdf, delivered 5 Oct).", 0.9),
            ("Rule", "Client emails and chats are never shared unless you add them yourself.", None),
            ("Rule", "Dated 6 Oct, so an EDF is needed; added to the export form pack.", None),
        ],
        "baseline": "A fixed rule cannot read the reviewer's request or pick the right documents. You would gather them by hand.",
        "prepared": ["Share three files with Razorpay's review team: invoice, signed scope of work, delivery readout."],
        "limits": ["Only these three files are shared, and only after you approve.", "No client emails or chats."],
        "approve_label": "Approve and share these three files",
        "after": [
            ("09:15", "Three files shared with Razorpay's review team.", False),
            ("Not published", "Razorpay does not publish review times. The agent shows the status here each morning.", False),
            ("After review and the EDF number", "Captured within 60 minutes; settles T+1.", True),
            ("T+1", "About ₹3,74,400 (at ₹88, before fees) reaches your ICICI account.", True),
        ],
        "audit": "Shared 3 documents with Razorpay review for SL-1054. Approved by Priya.",
    },
    # 7. Declined card, Larkspur
    {
        "slug": "sl-1043", "approved_at": "09:06", "journey_after": ["done", "wait", "todo", "todo", "todo", "todo"], "invoices": ["SL-1043"], "client": "Larkspur Labs Inc", "country": "US",
        "ccy": "USD", "amount": 2400.0, "bucket": "prepared", "rank": 7, "kind": "Declined",
        "title": "Larkspur's card payment was declined by their bank",
        "line": "Offer a US bank transfer, the way they paid in July and August.",
        "why_now": "The invoice is due on 15 Oct. The client's bank blocked a cross-border card payment on 9 Oct, and nobody has told them another way to pay.",
        "urgency": "Due in 3 days", "urgency_level": "medium",
        "journey": ["done", "stuck", "todo", "todo", "todo", "todo"],
        "facts": [
            ("9 Oct, 22:14 IST: Dana Whitfield tried to pay SL-1043 ($2,400) by Visa. Her bank declined it: \"Do not honour. Cross-border risk.\"", "Razorpay payment record"),
            ("Larkspur paid your July and August invoices by US bank transfer (ACH) into your USD account.", "Razorpay history"),
            ("No reply from Dana since the decline.", "Inbox"),
        ],
        "steps": [
            ("AI", "Read the decline text, \"Do not honour. Cross-border risk\": the client's bank blocked a cross-border payment, not a card or funds problem.", 0.93),
            ("Rule", "For a bank block, the next way to pay is a local bank transfer to your global account (policy, section 6). Retrying the same card usually fails again.", None),
            ("AI", "Drafted the note. Larkspur's accounts team has paid by US bank transfer twice, so that leads; an Apple Pay link is the second choice in case Dana prefers a card.", 0.91),
            ("Rule", "Limits: reminder 1 of 2; sent at 9:00 in Boston on Tuesday 13 October, because Monday 12 October is a US public holiday.", None),
        ],
        "baseline": "A fixed rule resends the same card link, which her bank is likely to block again.",
        "prepared": ["A short note from Priya to Dana with a bank transfer link and an Apple Pay link."],
        "draft_kind": "Email to Dana Whitfield, Larkspur Labs",
        "draft_subject": "Invoice SL-1043: an easier way to pay",
        "draft": [
            "Hi Dana,",
            "Your card payment for invoice SL-1043 ($2,400) didn't go through on Friday. Your bank declined it as an international payment, which sometimes happens with cross-border card payments.",
            "The simplest fix is a US bank transfer, as you did for our July and August invoices. The account details are on this secure page: [Pay by bank transfer]",
            "If you'd rather use a card, this Apple Pay link may get round the block: [Pay with Apple Pay]",
            "Thanks,",
            "Priya",
        ],
        "limits": ["Reminder 1 of 2 for this decline.", "Sent only in Dana's working hours, and not on a US public holiday (Monday 12 October is one).", "Stops at once if Dana replies that she has paid, will pay, or disputes it."],
        "approve_label": "Approve note",
        "after": [
            ("09:06", "Scheduled for Dana's next working day.", False),
            ("Tue 13 Oct, 18:30 IST", "Note sent at 9:00 in Boston.", False),
            ("Wed 14 Oct", "Dana pays $2,400 by ACH.", True),
            ("Wed 14 Oct", "The agent links the payment to SL-1043 by rule and adds SL-1043 to the next EDF pack (ICICI needs the number before capture).", True),
            ("After the EDF number", "Captured within 60 minutes; settles T+1; FIRA within 24 hours.", True),
        ],
        "audit": "Sent reminder 1 for SL-1043 with bank transfer and Apple Pay links. Approved by Priya.",
    },
    # 8. Copperline says already paid
    {
        "slug": "sl-1039", "approved_at": "09:10", "journey_after": ["done", "done", "done", "na", "wait", "todo"], "invoices": ["SL-1039"], "client": "Copperline Studios Pty Ltd", "country": "Australia",
        "ccy": "USD", "amount": 2725.0, "bucket": "prepared", "rank": 8, "kind": "Waiting for an invoice",
        "title": "Copperline says they paid SL-1039, and they did: $2,725 is sitting unlinked",
        "line": "Reminders stopped. Link the wire they sent on 6 Oct.",
        "why_now": "Ruth replied on 9 Oct that they paid. The agent found the wire waiting for an invoice.",
        "urgency": "Arrived 6 days ago", "urgency_level": "medium",
        "journey": ["done", "done", "stuck", "na", "todo", "todo"],
        "facts": [
            ("SL-1039, website redesign milestone 2, $2,750, dated 15 Sep.", "Zoho Books"),
            ("25 Sep: card attempt declined, 3-D Secure not completed. 30 Sep: reminder 1 sent, approved by you.", "Razorpay; audit log"),
            ("9 Oct, Ruth Ellery: \"We already paid this by wire last Friday, reference COPPERLINE SL1039.\"", "Inbox"),
            ("6 Oct: $2,725 by SWIFT from COPPERLINE GROUP PTY LTD, reference \"SL1039\". Waiting for invoice and buyer details.", "Razorpay MoneySaver"),
        ],
        "steps": [
            ("AI", "Read Ruth's reply: they say they have paid, around Friday 2 Oct, reference SL1039.", 0.97),
            ("Rule", "Said paid, so all reminders for SL-1039 stopped at once.", None),
            ("Rule", "Searched transfers from the last 14 days.", None),
            ("AI", "Match: the $2,725 wire. Reference SL1039, COPPERLINE GROUP PTY LTD is plausibly Copperline's group company, and $25 is a typical SWIFT charge.", 0.96),
            ("Rule", "Dated 15 Sep, before 1 Oct, so no EDF is needed and Razorpay can capture as soon as the invoice is attached.", None),
        ],
        "baseline": "A fixed rule keeps sending reminders to a client who has already paid, and leaves the wire unmatched.",
        "prepared": [
            "Attach SL-1039 and buyer details to the $2,725 wire; record $25 as bank charges.",
            "Remember COPPERLINE GROUP PTY LTD as a Copperline payer name.",
        ],
        "optional_draft": True,
        "draft_kind": "Separate, optional: a two-line thank-you to Ruth Ellery, Copperline Studios. It is not part of the approval above.",
        "draft_subject": "Thanks for paying SL-1039",
        "draft": ["Hi Ruth,", "Thanks, we've found your payment for SL-1039 and matched it. Sorry for the reminder.", "Priya"],
        "limits": ["Approving the link sends nothing to Copperline.", "The thank-you is a separate decision; if you send it, it goes at 9:00 in Melbourne (03:30 IST)."],
        "approve_label": "Approve link",
        "after": [
            ("09:10", "Invoice SL-1039 and buyer details attached; $25 recorded as charges.", False),
            ("10:10", "Captured within 60 minutes (no EDF needed for a September invoice).", True),
            ("T+1", "About ₹2,39,800 (at ₹88, before fees) reaches your ICICI account. FIRA within 24 hours.", True),
            ("Learned", "COPPERLINE GROUP PTY LTD now counts as Copperline.", False),
        ],
        "audit": "Stopped reminders for SL-1039; linked $2,725 from COPPERLINE GROUP PTY LTD. Approved by Priya.",
    },
    # 9. Saltmarsh 3DS failures, paused until today
    {
        "slug": "sl-1046", "approved_at": "09:07", "journey_after": ["done", "wait", "todo", "na", "todo", "todo"], "invoices": ["SL-1046"], "client": "Saltmarsh Media Ltd", "country": "UK",
        "ccy": "GBP", "amount": 950.0, "bucket": "prepared", "rank": 9, "kind": "Declined",
        "title": "Saltmarsh said they'd retry this week. One gentle note, with an easier way to pay",
        "line": "Paused until today. Offer Apple Pay or Google Pay, or a UK bank transfer.",
        "why_now": "On Friday 2 Oct Tom said he would try again the following week. That week has passed with no payment, so the pause ended this morning.",
        "urgency": "Pause ended today", "urgency_level": "low",
        "journey": ["done", "stuck", "todo", "na", "todo", "todo"],
        "facts": [
            ("SL-1046, editorial illustrations, £950, dated 29 Sep.", "Zoho Books"),
            ("1 Oct: two card attempts declined, \"3-D Secure authentication not completed\".", "Razorpay payment record"),
            ("2 Oct, Tom Hale: \"Your payment page keeps failing on my phone, I'll try again next week.\"", "Inbox"),
        ],
        "steps": [
            ("AI", "Read Tom's reply: he will retry in the week of 5 Oct, so the agent paused until that week was over (Mon 12 Oct).", 0.9),
            ("AI", "Read the decline text: 3-D Secure not completed, twice, on a phone.", 0.92),
            ("Rule", "For a failed card check on a phone, the next way to pay is a wallet (Apple Pay or Google Pay), which skips that step; a UK bank transfer to your GBP account is the fallback (policy, section 6).", None),
            ("AI", "Drafted the note in your tone: short, both links, no pressure.", 0.88),
            ("Rule", "Reminder 1 of 2; sent at 9:00 in London (13:30 IST).", None),
        ],
        "baseline": "A fixed rule sends the same card link again, which has already failed twice on his phone.",
        "prepared": ["A short note to Tom with a wallet link and a UK bank transfer link."],
        "draft_kind": "Email to Tom Hale, Saltmarsh Media",
        "draft_subject": "Invoice SL-1046: two easier ways to pay",
        "draft": [
            "Hi Tom,",
            "Following up on invoice SL-1046 (£950). The card check seems to fail on your phone, so here are two options that usually work:",
            "Pay with Apple Pay or Google Pay: [Pay with a wallet]",
            "Or pay by UK bank transfer to our GBP account: [Pay by bank transfer]",
            "Thanks,",
            "Priya",
        ],
        "limits": ["Reminder 1 of 2 for this decline.", "Sent only in Tom's working hours."],
        "approve_label": "Approve note",
        "after": [
            ("09:07", "Scheduled for Tom's working hours.", False),
            ("13:30 IST", "Note sent at 9:00 in London.", False),
            ("14:05 IST", "Tom pays £950 with Apple Pay.", True),
            ("14:06 IST", "The agent uploads SL-1046 by rule and the payment is captured (September invoice, no EDF).", True),
            ("Next cycle", "₹1,11,150 settles to ICICI; FIRA follows.", True),
        ],
        "audit": "Sent reminder 1 for SL-1046 with wallet and bank transfer links. Approved by Priya.",
    },
    # 10. Tidewater ambiguous
    {
        "slug": "sl-1052-1053", "approved_at": "09:12", "journey_after": ["done", "done", "done", "wait", "todo", "todo"], "invoices": ["SL-1052", "SL-1053"], "client": "Tidewater Health LLC", "country": "US",
        "ccy": "USD", "amount": 1500.0, "bucket": "answer", "rank": 10, "kind": "Needs your answer",
        "title": "$1,500 from Tidewater Health: which invoice is it for?",
        "line": "Two open invoices are exactly $1,500. The agent won't guess.",
        "why_now": "The money arrived on 8 Oct and cannot settle until it is linked to an invoice.",
        "urgency": "Arrived 4 days ago", "urgency_level": "medium",
        "journey": ["done", "done", "stuck", "todo", "todo", "todo"],
        "facts": [
            ("8 Oct: $1,500 by ACH from TIDEWATER HEALTH LLC, no reference.", "Razorpay MoneySaver"),
            ("Open: SL-1052, patient app UI phase 1, $1,500, dated 2 Oct; SL-1053, clinic website refresh, $1,500, dated 6 Oct.", "Zoho Books"),
        ],
        "steps": [
            ("Rule", "Two invoices fit exactly.", None),
            ("AI", "A slight lean towards SL-1052, the older one, but 0.58 is below your 0.80 threshold, so the agent asks.", 0.58),
        ],
        "baseline": "A fixed rule leaves it unmatched, with no question and no lean.",
        "prepared": ["Your choice: SL-1052, SL-1053, or a one-line question to Marcus at Tidewater."],
        "answers": ["It's SL-1052", "It's SL-1053", "Ask Tidewater"],
        "limits": ["Nothing is linked until you answer."],
        "approve_label": "It's SL-1052",
        "after": [
            ("09:12", "Linked to SL-1052; buyer details attached.", False),
            ("09:12", "SL-1052 is dated 2 Oct, so it joins the export form pack (ICICI needs the number before capture).", False),
            ("Learned", "Tidewater pays its oldest invoice first. Next time the agent's lean is stronger.", False),
            ("Still open", "SL-1053 stays open.", False),
        ],
        "audit": "Priya chose SL-1052 for $1,500 from TIDEWATER HEALTH LLC.",
    },
    # 11. Unknown payer
    {
        "slug": "quillon", "approved_at": "09:13", "journey_after": ["wait", "done", "wait", "todo", "todo", "todo"], "invoices": [], "client": "QUILLON DESIGNWORKS", "country": "Unknown",
        "ccy": "USD", "amount": 800.0, "bucket": "answer", "rank": 11, "kind": "Needs your answer",
        "title": "$800 from QUILLON DESIGNWORKS: the agent doesn't recognise this payer",
        "line": "No client or open invoice matches. Tell the agent who it's from.",
        "why_now": "The money arrived on 10 Oct and cannot settle without an invoice.",
        "urgency": "Arrived 2 days ago", "urgency_level": "low",
        "journey": ["todo", "done", "stuck", "todo", "todo", "todo"],
        "facts": [
            ("10 Oct: $800 by ACH from QUILLON DESIGNWORKS, reference \"logo refresh\".", "Razorpay MoneySaver"),
            ("No open invoice for $800; no client with a similar name; \"logo refresh\" appears in no invoice.", "Zoho Books"),
        ],
        "steps": [
            ("Rule", "No candidate invoice.", None),
            ("AI", "Most likely a new client who hasn't been invoiced yet.", None),
            ("Rule", "Razorpay cannot refund bank transfers, so if it isn't yours the agent prepares a note to Razorpay support instead.", None),
        ],
        "baseline": "A fixed rule leaves it unmatched with no explanation.",
        "prepared": ["Three answers to choose from."],
        "answers": ["New client: I'll raise the invoice in Zoho", "It's from an existing client", "Not ours: tell Razorpay support"],
        "limits": ["Nothing is linked or returned until you answer."],
        "approve_label": "New client: I'll raise the invoice in Zoho",
        "after": [
            ("09:13", "The agent watches Zoho for the new invoice.", False),
            ("When it appears", "The agent links it (exact amount and payer) and adds it to the export form pack if it is dated on or after 1 Oct.", False),
        ],
        "audit": "Priya said QUILLON DESIGNWORKS is a new client; waiting for the invoice in Zoho.",
    },
    # 12. Halcyon dispute: stopped
    {
        "slug": "sl-1044", "invoices": ["SL-1044"], "client": "Halcyon Retail Pte Ltd", "country": "Singapore",
        "ccy": "USD", "amount": 4100.0, "bucket": "stopped", "rank": 12, "kind": "Stopped",
        "title": "Halcyon disputes the hours on SL-1044. The agent has stopped",
        "line": "No more contact on this invoice. Your call.",
        "why_now": "Wei Ling replied on 8 Oct that they dispute the week 3 hours.",
        "urgency": "Stopped 8 Oct", "urgency_level": "low",
        "journey": ["done", "stuck", "todo", "na", "todo", "todo"],
        "facts": [
            ("SL-1044, e-commerce UI design weeks 1 to 4, $4,100, dated 28 Sep.", "Zoho Books"),
            ("3 Oct: card declined, card limit. 6 Oct: reminder 1 sent, approved by you.", "Razorpay; audit log"),
            ("8 Oct, Wei Ling Tan: \"We're disputing the hours billed for week 3. Please hold off until we've resolved it with Priya.\"", "Inbox"),
        ],
        "steps": [
            ("AI", "Read the reply: a dispute about the work, not a payment problem.", 0.97),
            ("Rule", "Dispute: stop all contact on this invoice and hand it to you.", None),
            ("Rule", "Nine-month deadline noted: 28 Jun 2027.", None),
        ],
        "baseline": "A fixed rule without reply reading sends reminder 2 to a client who is disputing the work.",
        "prepared": ["Nothing to approve. Halcyon is on do-not-contact for SL-1044."],
        "answers": ["I'll reply myself", "Resolved: resume", "I'll write it off in Zoho"],
        "limits": ["No messages to Halcyon about SL-1044 until you say so."],
        "approve_label": None,
        "after": [],
        "audit": "Stopped all contact on SL-1044 after a dispute; handed to Priya.",
    },
]

DONE = [
    {"invoice": "SL-1036", "client": "Kestrel Analytics GmbH", "ccy": "EUR", "amount": 3200.0, "home": "3 Oct",
     "note": "SEPA on 2 Oct, matched by rule, captured, settled 3 Oct, FIRA received. Dated 10 Sep, so no EDF."},
    {"invoice": "SL-1038", "client": "Bramble & Finch Ltd", "ccy": "GBP", "amount": 1100.0, "home": "1 Oct",
     "note": "Card captured 30 Sep, settled 1 Oct, FIRA received. Dated 12 Sep, so no EDF."},
]
NO_ACTION = [
    {"what": "Upwork payout", "ccy": "USD", "amount": 640.0, "date": "8 Oct",
     "note": "Platform payouts need no invoice upload on Razorpay. Nothing to do."},
]

INVOICES = [
    # invoice, client, date, service, ccy, amount, journey, status, slug
    ("SL-0981", "Copperline Studios Pty Ltd", "20 Jan 2026", "Pitch deck design", "USD", 1200.0, ["done", "stuck", "todo", "na", "todo", "todo"], "Unpaid; nine-month limit 20 Oct", "sl-0981"),
    ("SL-1036", "Kestrel Analytics GmbH", "10 Sep 2026", "Dashboard UX design", "EUR", 3200.0, ["done"] * 3 + ["na", "done", "done"], "Closed", None),
    ("SL-1038", "Bramble & Finch Ltd", "12 Sep 2026", "Brand refresh, phase 1", "GBP", 1100.0, ["done"] * 3 + ["na", "done", "done"], "Closed", None),
    ("SL-1039", "Copperline Studios Pty Ltd", "15 Sep 2026", "Website redesign, milestone 2", "USD", 2750.0, ["done", "done", "stuck", "na", "todo", "todo"], "Paid by wire; waiting to be linked", "sl-1039"),
    ("SL-1040", "Juniper Ridge Inc", "30 Sep 2026", "Product design sprint 1", "USD", 3000.0, ["done", "done", "stuck", "na", "todo", "todo"], "Paid with SL-1045; waiting to be linked", "sl-1040-1045"),
    ("SL-1043", "Larkspur Labs Inc", "1 Oct 2026", "Brand system design", "USD", 2400.0, ["done", "stuck", "todo", "todo", "todo", "todo"], "Card declined", "sl-1043"),
    ("SL-1044", "Halcyon Retail Pte Ltd", "28 Sep 2026", "E-commerce UI design, weeks 1 to 4", "USD", 4100.0, ["done", "stuck", "todo", "na", "todo", "todo"], "Disputed; agent stopped", "sl-1044"),
    ("SL-1045", "Juniper Ridge Inc", "3 Oct 2026", "Product design sprint 2", "USD", 2400.0, ["done", "done", "stuck", "todo", "todo", "todo"], "Paid with SL-1040; needs EDF", "sl-1040-1045"),
    ("SL-1046", "Saltmarsh Media Ltd", "29 Sep 2026", "Editorial illustrations", "GBP", 950.0, ["done", "stuck", "todo", "na", "todo", "todo"], "Card failed twice; client retrying", "sl-1046"),
    ("SL-1047", "Larkspur Labs Inc", "5 Oct 2026", "Website build, sprint 2", "USD", 2000.0, ["done", "done", "stuck", "todo", "todo", "todo"], "Paid $1,950; waiting to be linked", "sl-1047"),
    ("SL-1051", "Bramble & Finch Ltd", "7 Oct 2026", "UX research and design", "GBP", 1800.0, ["done", "done", "stuck", "todo", "todo", "todo"], "Card authorised; refunds in 1 day", "sl-1051"),
    ("SL-1052", "Tidewater Health LLC", "2 Oct 2026", "Patient app UI, phase 1", "USD", 1500.0, ["done", "wait", "todo", "todo", "todo", "todo"], "$1,500 arrived; this one or SL-1053?", "sl-1052-1053"),
    ("SL-1053", "Tidewater Health LLC", "6 Oct 2026", "Clinic website refresh", "USD", 1500.0, ["done", "wait", "todo", "todo", "todo", "todo"], "$1,500 arrived; this one or SL-1052?", "sl-1052-1053"),
    ("SL-1054", "Fernhill Analytics Ltd", "6 Oct 2026", "Data product design: discovery", "GBP", 3200.0, ["done", "done", "done", "todo", "stuck", "todo"], "Under review; documents ready", "sl-1054"),
]

EDF_OCTOBER = [
    # invoice, client, country, service, ccy, amount, payment status, in pack now?, code note
    ("SL-1043", "Larkspur Labs Inc", "US", "Brand system design", "USD", 2400.0, "Card declined; not paid yet", "Monthly EDF, or the pack once paid", "Design: confirm code"),
    ("SL-1045", "Juniper Ridge Inc", "CA", "Product design sprint 2", "USD", 2400.0, "Paid 7 Oct; waiting for EDF number", "Today's pack", "Design: confirm code"),
    ("SL-1047", "Larkspur Labs Inc", "US", "Website build, sprint 2", "USD", 2000.0, "Paid 9 Oct ($1,950); waiting for EDF number", "Today's pack", "P0802 fits"),
    ("SL-1051", "Bramble & Finch Ltd", "UK", "UX research and design", "GBP", 1800.0, "Card authorised 10 Oct", "Monthly EDF, due 30 Nov", "Design: confirm code"),
    ("SL-1052", "Tidewater Health LLC", "US", "Patient app UI, phase 1", "USD", 1500.0, "Paid 8 Oct, once you confirm the invoice", "Pack, after your answer", "Design: confirm code"),
    ("SL-1053", "Tidewater Health LLC", "US", "Clinic website refresh", "USD", 1500.0, "Not paid yet", "Monthly EDF, due 30 Nov", "P0802 fits"),
    ("SL-1054", "Fernhill Analytics Ltd", "UK", "Data product design: discovery", "GBP", 3200.0, "Paid 9 Oct; under review", "Today's pack", "Design: confirm code"),
]

PLAYBOOK = [
    # (group, situation, how it is spotted, who decides, what the agent does, what it never does, demo slug)
    ("The payment never arrived", "Card declined: the client's bank blocked a cross-border payment", "Decline reason on the payment record", "Rule, then AI", "Offers a local bank transfer to your global account, or a wallet if no local account exists for that currency", "Resend the same card link that was just blocked", "sl-1043"),
    ("The payment never arrived", "Card declined: 3-D Secure failed or the card is not enrolled", "Decline reason", "Rule, then AI", "Offers Apple Pay or Google Pay; offers a bank transfer instead if the client is on a desktop or has paid by transfer before", "Retry the card again and again", "sl-1046"),
    ("The payment never arrived", "Card declined: billing address mismatch (US, UK and Canada cards)", "Decline reason; card country", "Rule", "Asks the client to retry once with the address their bank holds; then a bank transfer", "Ask for the card number or address by email", None),
    ("The payment never arrived", "Card declined: insufficient funds or card limit", "Decline reason", "Rule", "Asks when they would like to pay and offers a bank transfer", "Retry rapidly", None),
    ("The payment never arrived", "Card blocked by the client's bank after repeated attempts", "Decline reason; attempt count", "Rule", "Stops card attempts; bank transfer only", "Trigger more fraud blocks", None),
    ("The payment never arrived", "International cards not switched on for your account", "Decline reason", "Rule", "Offers the client a bank transfer and shows you how to request activation (Dashboard, International payments)", "Blame the client", None),
    ("The payment never arrived", "The client says they will pay on a date", "Client's reply", "AI", "Pauses until that date", "Remind before the date", None),
    ("The payment never arrived", "The client says they have already paid", "Client's reply", "AI, then rule", "Stops reminders; searches transfers from the last 14 days; links or asks for the reference", "Keep chasing", "sl-1039"),
    ("The payment never arrived", "The client disputes the invoice or the work", "Client's reply", "AI, then rule", "Stops all contact on that invoice and hands it to you", "Argue, discount or remind", "sl-1044"),
    ("The payment never arrived", "The client is on your do-not-contact list", "Your list", "Rule", "Prepares the note for you to send yourself", "Contact them", None),
    ("The payment never arrived", "Automatic out-of-office reply", "Client's reply", "AI", "Pauses until the return date; with no return date it keeps waiting within the usual limits", "Send while they are away", None),
    ("The payment never arrived", "A decline that fits none of the listed reasons", "Decline reason", "Rule", "Offers a bank transfer, the safest route, and shows you the raw decline text", "Invent a reason", None),
    ("The payment never arrived", "A client's public holiday", "Client's country and calendar", "Rule", "Waits for the next working day in the client's country (Monday 12 October 2026 is a US public holiday)", "Send on a holiday", "sl-1043"),
    ("The payment never arrived", "Someone else now handles payments", "Client's reply", "AI", "Asks you to update the contact in Zoho", "Change contacts by itself", None),
    ("The payment never arrived", "The client asks for bank details", "Client's reply", "AI", "Prepares your global account details for approval", "Send account details without approval", None),
    ("The payment never arrived", "Two reminders already sent for this decline", "Reminder count", "Rule", "Hands it to you", "Send a third", None),
    ("The payment never arrived", "An invoice is unpaid with nothing gone wrong", "Due date only", "Not this agent", "Leaves it to the RazorpayX Receivables Agent", "Duplicate reminders", None),
    ("Money arrived but is stuck", "A card payment is waiting for its invoice, with the 3-day refund clock running", "Payment status and authorisation time", "Rule", "Uploads the matching invoice after approval, most urgent first", "Let it refund", "sl-1051"),
    ("Money arrived but is stuck", "A bank transfer is waiting for an invoice and buyer details", "MoneySaver status", "Rule, then AI", "Finds the invoice in Zoho and attaches it with buyer details after approval", "Attach an invoice it is unsure about", "sl-1047"),
    ("Money arrived but is stuck", "The payer's name differs from the client (parent company, payment service)", "Payer name, reference, known aliases", "AI", "Matches on evidence and remembers the alias once you approve", "Link to a different client without strong evidence", "sl-1047"),
    ("Money arrived but is stuck", "Short by a bank charge (at most $50, £40 or €45, and 3%)", "Amount gap", "Rule", "Links and records the charge; closes it by declaration if under ₹10 lakh", "Chase the client for bank fees", "sl-1047"),
    ("Money arrived but is stuck", "Short by more than a bank charge, no part payment stated", "Amount gap", "Rule", "Asks you", "Guess", None),
    ("Money arrived but is stuck", "A stated part payment", "Reference or note", "AI", "Links it as a part payment; the rest stays open", "Mark the invoice paid", None),
    ("Money arrived but is stuck", "One transfer pays several invoices", "Reference; amounts sum exactly", "AI", "Splits it across the invoices", "Split across different clients", "sl-1040-1045"),
    ("Money arrived but is stuck", "Two open invoices fit equally", "Same client, same amount, no useful reference", "Rule", "Asks you, with its lean and its confidence", "Pick one silently", "sl-1052-1053"),
    ("Money arrived but is stuck", "Unknown payer", "No client or invoice fits", "Rule, then AI", "Asks you; if it isn't yours, prepares a note to Razorpay support (bank transfers cannot be refunded)", "Return or keep the money by itself", "quillon"),
    ("Money arrived but is stuck", "Possible duplicate: the only matching invoice is already paid", "Invoice status", "Rule", "Asks you whether to credit or return it", "Treat it as new money", None),
    ("Money arrived but is stuck", "Overpayment, or a payment in a different currency from the invoice", "Amount or currency gap", "Rule", "Asks you; never rounds the difference away", "Guess which invoice absorbs the difference", None),
    ("Money arrived but is stuck", "You approved a link to the wrong invoice", "Your correction, before or after capture", "Rule, then AI", "Before capture: unlinks and asks again. After capture: prepares a correction note to Razorpay support and the bank for your approval, demotes the payer name it learned, and switches auto-approve off until 20 more matches are confirmed", "Hide the mistake or edit the audit log", None),
    ("Money arrived but is stuck", "A review team asks for documents", "Razorpay's request", "AI", "Prepares a pack from Zoho and Drive for approval", "Share client emails or chats", "sl-1054"),
    ("Money arrived but is stuck", "Platform payouts (Amazon, Upwork, Freelancer)", "Payer is a platform", "Rule", "Nothing; no invoice needed", "Create work", None),
    ("Declaring and closing", "Firm with invoices dated on or after 1 Oct 2026: EDF needed", "Entity type; invoice date", "Rule", "Prepares the month's EDF data; tracks the 30-day deadline", "File with the bank", "edf-pack"),
    ("Declaring and closing", "Individual on personal-nature contracts", "Entity type", "Rule", "Shows that no EDF is needed (RBI, 7 Oct 2026) and updates when RBI's FAQs arrive", "Ask for forms nobody needs", None),
    ("Declaring and closing", "Account settles to ICICI: EDF number needed before capture", "Settlement bank", "Rule", "Prepares the EDF early for payments already waiting", "Leave money blocked until month end", "edf-pack"),
    ("Declaring and closing", "Invoice dated before 1 Oct 2026", "Invoice date", "Rule", "No EDF; capture can go ahead", "Ask for an EDF", "sl-1039"),
    ("Declaring and closing", "The purpose code may not fit the service", "Invoice text against the account's code", "AI", "Flags it and asks you to confirm with your bank or CA", "Guess a code", "edf-pack"),
    ("Declaring and closing", "Invoice up to ₹10 lakh", "Amount", "Rule", "Uses the self-declaration route", "Ask for papers that are not needed", "edf-pack"),
    ("Declaring and closing", "Invoice above ₹10 lakh", "Amount", "Rule", "Prepares the invoice, FIRA and matching instructions the bank needs", "Skip documents", None),
    ("Declaring and closing", "Nine-month realisation deadline close", "Invoice date", "Rule, then AI", "Drafts the extension request to the bank", "Chase the client (that is the Receivables Agent's job)", "sl-0981"),
    ("Declaring and closing", "FIRA missing after settlement", "Settlement without a FIRA", "Rule", "Prepares a support request to Razorpay", "Wait silently", None),
    ("Keeping the agent safe", "Confidence below 0.80", "Model confidence", "Rule", "Asks you instead of acting", "Guess with money", "sl-1052-1053"),
    ("Keeping the agent safe", "You edit a draft", "Your edits", "AI", "Learns your tone for next time", "Send the old version", None),
    ("Keeping the agent safe", "You say no to a suggestion", "Your answer", "Rule", "Does not suggest it again for 30 days", "Nag", None),
    ("Keeping the agent safe", "You pause the agent", "Your setting", "Rule", "Keeps the list up to date; sends nothing", "Act while paused", None),
    ("Keeping the agent safe", "The AI service is down", "Health check", "Rule", "Runs on rules only; drafts nothing", "Fail silently", None),
    ("Keeping the agent safe", "Zoho is disconnected", "Connection check", "Rule", "Asks you to upload invoices", "Invent invoice data", None),
    ("Keeping the agent safe", "A message tries to instruct the agent, or asks for documents or details to go somewhere new", "Message content; sender's domain", "AI, then rule", "Flags it as suspicious, pauses messages to that client, hands it to you", "Follow instructions inside client messages or click links", None),
    ("Keeping the agent safe", "Every action", "All of the above", "Rule", "Writes it to the audit log with who approved it", "Act without a record", None),
    ("Keeping the agent safe", "Stuck with Razorpay or the bank", "No progress after a set time", "Rule", "Prepares a case for Razorpay support with the evidence", "Promise dates for others", None),
]

LEARNING_ROUTES = [
    ("Client's bank blocked a cross-border card payment", "Bank transfer link", "8 of 10"),
    ("Client's bank blocked a cross-border card payment", "The same card link again", "2 of 7"),
    ("3-D Secure failed on a phone", "Apple Pay or Google Pay", "5 of 6"),
    ("3-D Secure failed on a desktop", "Bank transfer link", "4 of 5"),
    ("Billing address mismatch", "Retry with the bank's address", "3 of 4"),
]
LEARNING_ALIASES = [
    ("LARKSPUR HOLDINGS LLC", "Larkspur Labs Inc", "Confirmed by you, 9 Sep"),
    ("COPPERLINE GROUP PTY LTD", "Copperline Studios Pty Ltd", "Proposed today; saved when you approve SL-1039"),
    ("WISE US INC (reference names the client)", "Read from the reference", "General rule"),
]
LEARNING_TONE = [
    "You shortened two drafts and removed \"Kindly\", so drafts are now shorter and never use it.",
    "You sign off as \"Priya\", not \"Regards, Priya\".",
]
LEARNING_NOS = [
    ("Offer Apple Pay to Kestrel Analytics (they always pay by SEPA)", "28 Sep", "Not suggested again before 28 Oct"),
]

AUDIT = [
    ("12 Oct, 09:00", "Agent", "Morning run: 12 open invoices and 1 unknown payment need attention; 9 prepared, 2 questions, 1 stopped."),
    ("12 Oct, 09:00", "Rule", "Pause on SL-1046 ended (the date Tom gave)."),
    ("9 Oct, 18:40", "AI, then rule", "Read Ruth's reply on SL-1039 (says paid); stopped reminders."),
    ("8 Oct, 14:22", "AI, then rule", "Read Wei Ling's reply on SL-1044 (dispute); stopped all contact; handed to Priya."),
    ("6 Oct, 18:30", "Agent", "Sent reminder 1 for SL-1044. Approved by Priya at 09:12."),
    ("3 Oct, 10:15", "Rule", "SL-1036 closed: settled, FIRA received."),
    ("2 Oct, 16:40", "Rule", "Linked SEPA €3,200 to SL-1036 (exact match)."),
    ("2 Oct, 11:20", "AI", "Read Tom's reply on SL-1046 (will retry next week); paused until 12 Oct."),
    ("30 Sep, 18:30", "Agent", "Sent reminder 1 for SL-1039. Approved by Priya at 10:02."),
    ("9 Sep, 11:05", "You", "Confirmed LARKSPUR HOLDINGS LLC is Larkspur Labs' parent company."),
]

SETTINGS = [
    ("Review first", "On", "Every message, upload and share needs your approval."),
    ("Auto-approve low-risk steps", "Off", "Available after 20 right matches in a row (the agent is at 31). It would cover only invoice uploads matched at 0.98 or above."),
    ("Reminders per declined payment", "2", "Then the agent hands it to you."),
    ("Client hours", "Weekdays, 09:00 to 18:00 in the client's time zone, not on their public holidays", "Nothing is sent at night, at weekends or on a public holiday in the client's country."),
    ("Confidence needed to suggest", "0.80", "Below this, the agent asks."),
    ("Do-not-contact", "Halcyon Retail (SL-1044, dispute)", "Added automatically after the dispute; remove it here."),
    ("Zoho Books", "Read-only: invoices and clients", "The agent never edits invoices."),
    ("Google Drive \"Contracts\"", "Read-only, only for packs you approve", "Nothing is shared without approval."),
    ("Email", "Drafts sent from priya@saffronloop.example after approval", "Replies to these notes are read; nothing else in your inbox."),
    ("AI service", "Running. If it is down, rules only", "Drafts pause; deadlines and limits keep working."),
]


def build():
    items = []
    for it in ITEMS:
        it = dict(it)
        if it["ccy"]:
            it["display"] = f"{SYM[it['ccy']]}{it['amount']:,.0f}"
            it["inr"] = inr(it["ccy"], it["amount"])
        items.append(it)
    # the export form pack releases B, H and J
    pack = next(i for i in items if i["slug"] == "edf-pack")
    pack["inr"] = sum(i["inr"] for i in items if i["slug"] in ("sl-1047", "sl-1040-1045", "sl-1054"))
    pack["display"] = "3 payments"
    money_items = [i for i in items if i["slug"] != "edf-pack"]
    arrived = [i for i in money_items if i["journey"][1] == "done"]
    not_paid = [i for i in money_items if i["journey"][1] != "done"]
    data = {
        "today": "Monday 12 October 2026", "run_time": "09:00 IST",
        "fx": FX, "merchant": MERCHANT, "stages": STAGES, "items": items,
        "totals": {
            "not_home_inr": sum(i["inr"] for i in money_items),
            "arrived_inr": sum(i["inr"] for i in arrived),
            "not_paid_inr": sum(i["inr"] for i in not_paid),
            "home_14d_inr": sum(inr(d["ccy"], d["amount"]) for d in DONE),
            "count": len(money_items),
            "arrived_count": len(arrived),
            "not_paid_count": len(not_paid),
        },
        "done": [dict(d, inr=inr(d["ccy"], d["amount"]), display=f"{SYM[d['ccy']]}{d['amount']:,.0f}") for d in DONE],
        "no_action": [dict(d, inr=inr(d["ccy"], d["amount"]), display=f"{SYM[d['ccy']]}{d['amount']:,.0f}") for d in NO_ACTION],
        "invoices": [dict(invoice=a, client=b, date=c, service=d, ccy=e, amount=f, display=f"{SYM[e]}{f:,.0f}",
                          inr=inr(e, f), journey=g, status=h, slug=s) for a, b, c, d, e, f, g, h, s in INVOICES],
        "edf_october": [dict(invoice=a, client=b, country=c, service=d, ccy=e, amount=f, display=f"{SYM[e]}{f:,.0f}",
                             inr=inr(e, f), payment=g, when=h, code=k) for a, b, c, d, e, f, g, h, k in EDF_OCTOBER],
        "playbook": [dict(group=a, situation=b, signal=c, decides=d, does=e, never=f, slug=g) for a, b, c, d, e, f, g in PLAYBOOK],
        "learning": {"routes": LEARNING_ROUTES, "aliases": LEARNING_ALIASES, "tone": LEARNING_TONE, "nos": LEARNING_NOS},
        "audit": AUDIT, "settings": SETTINGS,
    }
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "demo.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    t = data["totals"]
    print("items", len(items), "not home", t["not_home_inr"], "arrived", t["arrived_inr"], "not paid", t["not_paid_inr"],
          "pack", pack["inr"], "home 14d", t["home_14d_inr"], "playbook", len(PLAYBOOK))


if __name__ == "__main__":
    build()
