# Homeward

**Every overseas invoice, home and closed.**

Homeward is a concept prototype for the Razorpay AI x PM Build Challenge at ISB (October 2026), Track 2, "Recover and Grow with AI". It is not a Razorpay product and is not affiliated with or endorsed by Razorpay. Every merchant, client, invoice, email and amount in it is made up.

## What it is
An agent, imagined inside Razorpay's Agent Studio, for small Indian services firms (agencies, SaaS firms, small IT shops) paid by overseas clients through Razorpay. It treats the **invoice** as the unit of work: an invoice is done only when the money is paid, linked to it, declared on the export form where required, in the bank and closed.

Each morning it lists the money that is not home yet, works out why, and prepares the fix. The owner approves, edits or stops each step. It covers three areas:
1. **Declined international payments:** it picks the next way to pay (bank transfer, wallet, retry with the right address) and drafts a short note.
2. **Money that arrived but is stuck:** it links payments to invoices when the payer, amount or reference differs, splits combined payments, handles bank charges and part payments, and prepares document packs for reviews.
3. **Export declaration forms (EDF) and closing the paperwork:** which invoices need an EDF and when (including the ICICI rule that blocks capture until an EDF number exists), purpose-code checks, small-shortfall declarations and the nine-month deadline.

Rules handle deadlines, limits and exact matches. AI handles judgement: messy matches, client replies in other languages, the choice of payment route, and drafts. Below 0.80 confidence it asks.

## What is in this repository
```
docs/            the website (GitHub Pages serves this folder); docs/llms.txt is a plain-text summary
agent/policy.md  the agent's rulebook (v1.2); sections 1 to 10 were the only instruction the AI received in the tests
data/demo.json   the demo merchant, invoices and prepared items (generated)
eval/            blind test sets: inputs, answer keys, agent outputs, rules-baseline outputs, scores
tools/           standard-library Python: demo data, test sets, two baselines, scoring, site build, QA
```

## View it
Open `docs/index.html` in a browser, or run `python3 -m http.server --directory docs 8000` and visit `http://localhost:8000`.

## Publish it on GitHub Pages
1. Create a new **public** repository on GitHub and upload everything in this folder (on github.com: Add file, Upload files, then drag the folders in).
2. In the repository: **Settings**, **Pages**. Under "Build and deployment", choose **Deploy from a branch**, branch **main**, folder **/docs**, then **Save**.
3. After a minute the site is live at `https://<your-username>.github.io/<repository-name>/`.
4. Check it in a private browser window (logged out) and on a phone.
5. Optional: put the repository and build log links in `tools/config.json` and run `python3 tools/build_site.py` so every page footer links to them.

## Rebuild
Needs Python 3.9 or later and nothing else (standard library only); `qa.py` also needs Playwright with Chromium.
```
python3 tools/demo_data.py     # demo data -> data/demo.json
python3 tools/baseline.py      # naive rules -> eval/outputs/baseline_*.json
python3 tools/baseline_fair.py # fair rules -> eval/outputs/fair_*.json
python3 tools/score.py         # scores -> eval/outputs/scores.json
python3 tools/build_site.py    # pages -> docs/
python3 tools/qa.py            # link, label, dash, spelling and phone-layout checks, screenshots (needs Playwright with Chromium)
```

## The blind test
- `tools/make_tests.py` generates the standard set (120 cases) with answer keys.
- The hard set (60 cases) was written by a separate AI instance asked to break the agent; the safety set (10 cases) tests instructions hidden in messages and references; the fresh set (36 cases, `eval/inputs/fresh_*.json`, notes in `eval/FRESH_SET_NOTES.md`) was written after the build by a second-judge pass with only the policy in view, never the keys.
- A fresh AI instance (Claude) played the agent on each set. It saw only sections 1 to 10 of `agent/policy.md` and the case inputs, never the answer keys. Its decisions are stored in `eval/outputs/agent_*.json`.
- Two rule baselines ran on the same cases: `tools/baseline.py` (naive: exact matches and keywords) and `tools/baseline_fair.py` (a rule set that runs without a model, written from the policy by a separate AI instance that saw the inputs but not the answer keys: fuzzy invoice numbers, bank-charge tolerance, sums, aliases, a decline-code table, phrase rules with negation and a small multilingual vocabulary). `tools/score.py` scores all three against the keys and writes `eval/outputs/scores.json`.

Result, 226 cases: the agent matched the answer key on 225 (its one disagreement is a gap in the policy, since both labels mean "keep waiting"); the fair rules on 224, linking money once where the policy says ask; the naive rules on 103, with 35 serious mistakes and ₹8.6 lakh linked to the wrong invoice.

**Read the results with care.** The published sets were written by AI from the same policy, and a fair rule set written from the policy matches the agent on all of them: where the input is structured and the policy is written down, rules are enough, and the product uses rules there. The model earns its place on what these cases cannot hold: real decline text, real email in other languages, invoice PDFs and bank narrations. The fresh set is the first look at that gap. A pilot with real exporters and a holdout group is the real test.

## What is real and what is made up
- **Real:** the rules and their sources (RBI FEMA 23(R)/2026-RB; Razorpay docs and blogs), Razorpay's products and list fees, the test method and its results on the published sets.
- **Made up:** the merchant, clients, invoices, emails, amounts, learning history and every step marked "simulated".
- **Not built:** connections to Razorpay, banks, Zoho or email, and live AI calls. The AI outputs shown on the site were produced with Claude during the build and stored.
- **Not tested:** real bank narrations, real email threads, real decline text; no merchant was interviewed. The public quotes on the site are cited by role and date.

## Pages
Today, Invoices, Export forms, Controls (the merchant's tools); How it works, Test results, Playbook, Learning, For judges and a rules-only mode (reading pages); 12 item pages and 11 "after you approve" pages. The site uses IBM Plex from Google Fonts with system fallbacks; it reads the same without them and without JavaScript.
