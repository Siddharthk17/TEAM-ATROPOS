# ATROPOS Finance AI

**Multi-agent financial intelligence powered by Google Gemini 2.0 Flash**

ATROPOS uses 4 specialized AI agents with strict Pydantic schemas to analyze bank statements, detect anomalies, forecast spending, and generate actionable savings plans — all in seconds.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CSV Upload / Demo Mode                     │
│                     (HDFC / SBI / ICICI / Any Bank)               │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │   Column Mapper    │  ← Gemini auto-detects columns
                  │   (Pydantic JSON)  │
                  └─────────┬─────────┘
                            │
              ┌─────────────▼──────────────┐
              │     Agent 1: Sanitizer      │  ← Cleans narrations → merchant + category
              │     (Pydantic: CleanedBatch)│
              └─────────────┬──────────────┘
                            │
         ┌──────────────────▼───────────────────┐
         │     Agent 2: Forensic Auditor         │
         │   Subscription Creep │ Hidden Fees    │  ← 5 anomaly detection types
         │   Weekend Inflation │ Duplicates      │
         │   Spending Spikes                     │
         │   (Pydantic: AnomalyReport)           │
         └──────────────────┬───────────────────┘
                            │
         ┌──────────────────▼───────────────────┐
         │     Agent 3: Wealth Architect         │  ← Brutal 3-step savings plan
         │     (Pydantic: WealthStrategy)        │
         └──────────────────┬───────────────────┘
                            │
         ┌──────────────────▼───────────────────┐
         │     Forecast Engine                   │  ← 30-day projection + trends
         └──────────────────┬───────────────────┘
                            │
         ┌──────────────────▼───────────────────┐
         │     Agent Debate (Meta-Analyst)       │  ← Synthesizes all findings
         └──────────────────┬───────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │      Dashboard + Reports    │
              │  11 Charts │ PDF │ Chat     │
              └────────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **Universal CSV Parser** | Auto-detects columns from any Indian bank format |
| **Pydantic Structured Output** | Every LLM call enforces JSON schema — zero malformed output |
| **11 Interactive Charts** | Sankey, donut, area, bar, scatter, velocity, MoM comparison |
| **Forensic Audit** | Detects subscription creep, hidden fees, weekend inflation, duplicates, spikes |
| **30-Day Forecast** | Trend-based projection per category |
| **Peer Benchmarking** | Compare against Indian urban household averages |
| **What-If Simulator** | Model spending cuts and see projected savings |
| **Agent Debate** | Meta-analysis synthesizing all agent findings |
| **PDF/TXT/CSV Reports** | Downloadable multi-page styled reports |
| **Audio Summary** | Browser TTS reads your financial briefing |
| **Natural Language Chat** | Ask anything about your spending data |
| **Token Usage Tracking** | Full observability of LLM cost per agent |

## Tech Stack

- **LLM:** Google Gemini 2.0 Flash via `google-genai` SDK
- **Structured Output:** Pydantic v2 + `response_schema` for guaranteed JSON
- **Frontend:** Streamlit 1.54+ with custom CSS
- **Charts:** Plotly Graph Objects (11 chart types)
- **Reports:** fpdf2 for PDF generation
- **Data:** Pandas + NumPy

## Quick Start

```bash
# Clone and install
cd fin-sentinel
pip install -r requirements.txt

# Set your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Run
streamlit run app.py
```

## Metrics

- Processes **500+ transactions in <5 seconds**
- **4 LLM calls** total (batched sanitizer + auditor + architect + debate)
- **~15K tokens** per full analysis (~$0.001 cost)
- **Zero crashes** — every agent has rule-based fallback
- **6 Pydantic schemas** enforce structured output

## Sample Bank Formats

Included in `samples/` directory:
- `hdfc_statement.csv` — HDFC Bank (Debit/Credit columns)
- `sbi_statement.csv` — SBI (Withdrawal/Deposit columns)
- `icici_statement.csv` — ICICI Bank (single Amount column)

## License

MIT
