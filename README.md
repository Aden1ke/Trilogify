# Trilogify

**Tri** → Trial matching  
**Log** → Evidence trail / audit log (every claim cites a FHIR resource ID)  
**Ify** → Intelligent automation  

A published MCP server on Prompt Opinion's Marketplace that reasons clinical
trial eligibility criterion-by-criterion against a patient's verified FHIR
record — returning cited evidence for every decision instead of a
keyword-matched list.

**All patient data is synthetic, sourced from the SMART Health IT FHIR R4
public sandbox (r4.smarthealthit.org). No real PHI is used.**

---

## The problem Trilogify solves

Every existing ClinicalTrials MCP server does keyword matching:
"lung cancer" → list of trials. No reasoning. No connection to the patient's
actual record. No explanation of which criterion the patient fails.

Trilogify reads each eligibility criterion as a natural language sentence and
reasons it against the patient's verified FHIR resources, returning:

- **Met** — with the specific FHIR resource ID as evidence
- **Not Met** — with the specific FHIR resource ID as evidence  
- **Insufficient Data** — stating exactly what is missing from the record

Hallucination is structurally impossible: if the data is not in the FHIR
record, the status is "Insufficient Data" — not a guess.

---

## The four tools

| # | Tool | What it does |
|---|------|--------------|
| 1 | `fetch_patient_clinical_profile` | Pulls conditions, medications, labs from SMART FHIR sandbox — every item cites its FHIR resource ID |
| 2 | `fetch_candidate_trials` | Queries ClinicalTrials.gov using patient's actual FHIR conditions |
| 3 | `reason_eligibility` | Core differentiator — LLM reasons each criterion against FHIR data, returns Met/Not Met/Insufficient Data with citations |
| 4 | `generate_screening_memo` | Full clinical document: ranked trials, evidence tables, items to verify, draft coordinator outreach |

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. Run locally
```bash
python main.py
```

---

## Deploy to Railway (for Prompt Opinion Marketplace)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Set `ANTHROPIC_API_KEY` as an environment variable in your Railway dashboard.  
Your server URL will be: `https://trilogify.railway.app` (or similar)

---

## Register on Prompt Opinion Marketplace

1. Go to **app.promptopinion.ai**
2. Navigate to Marketplace → Add MCP Server
3. Enter your Railway URL
4. Set server name: **Trilogify**
5. Paste the description below
6. Publish

### Marketplace description
```
Trilogify — FHIR-Grounded Clinical Trial Screener

Tri → Trial matching. Log → Evidence audit trail. Ify → Intelligent automation.

Unlike keyword-matching MCP tools, Trilogify reads each eligibility criterion
as a natural language sentence and reasons it against the patient's verified
FHIR record — returning Met / Not Met / Insufficient Data with the specific
FHIR resource ID that drove every decision.

Tools: fetch_patient_clinical_profile, fetch_candidate_trials,
reason_eligibility, generate_screening_memo.

All patient data is synthetic (SMART Health IT FHIR R4 sandbox).
```

---

## Example patient IDs (SMART sandbox — synthetic)

Browse all patients at: `https://r4.smarthealthit.org/Patient?_count=20`

---

## Data compliance

> All patient data used by Trilogify is synthetic, sourced from the
> SMART Health IT FHIR R4 public sandbox (r4.smarthealthit.org).
> No real Protected Health Information (PHI) is used or stored.
> Trilogify complies with the hackathon's data integrity requirements.