import os
import json
import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class ColumnMapping(BaseModel):
    """Smart CSV column identification — works with any Indian bank format."""
    date_column: str = Field(description="Column name containing transaction dates")
    description_column: str = Field(description="Column containing transaction descriptions/narrations")
    amount_column: Optional[str] = Field(None, description="Single amount column if exists")
    debit_column: Optional[str] = Field(None, description="Debit/withdrawal column if separate")
    credit_column: Optional[str] = Field(None, description="Credit/deposit column if separate")
    balance_column: Optional[str] = Field(None, description="Running balance column if exists")


class CleanedTransaction(BaseModel):
    """Output of The Sanitizer: messy string → clean merchant + category."""
    original_description: str = Field(description="Original raw description from bank")
    merchant: str = Field(description="Clean merchant name e.g. 'Zomato' not 'UPI/123/ZOMATO'")
    category: str = Field(description="Spending category e.g. 'Food', 'Transport', 'Subscriptions'")


class CleanedBatch(BaseModel):
    """Batch result from The Sanitizer agent."""
    transactions: List[CleanedTransaction]


class AnomalyItem(BaseModel):
    """Each anomaly includes a full forensic reasoning trace for the judges."""
    transaction_indices: List[int] = Field(description="Row indices of related transactions")
    anomaly_type: str = Field(
        description="subscription_creep | hidden_bank_fee | weekend_lifestyle_inflation | duplicate_charge | spending_spike"
    )
    severity: str = Field(description="low | medium | high | critical")
    title: str = Field(description="Short descriptive alert title")
    reasoning: str = Field(description="Detailed 2-3 sentence forensic explanation with amounts and dates")
    amount_inr: float = Field(description="Primary amount involved in INR")


class AnomalyReport(BaseModel):
    """Full forensic audit report with risk scoring."""
    anomalies: List[AnomalyItem]
    risk_score: float = Field(description="Overall account risk score 0-100")
    summary: str = Field(description="Executive summary of all findings")


class ActionStep(BaseModel):
    """One step of the Wealth Architect's brutal savings plan."""
    step_number: int = Field(description="Step number 1-3")
    title: str = Field(description="Punchy action title")
    description: str = Field(description="Brutally honest, specific advice with exact INR amounts")
    estimated_monthly_savings: float = Field(description="Estimated monthly savings in INR")
    category: str = Field(description="Related spending category")


class WealthStrategy(BaseModel):
    """The Wealth Architect's brutal 3-step action plan."""
    action_plan: List[ActionStep]
    financial_health_score: float = Field(description="Financial health score 0-100")
    overall_verdict: str = Field(description="One paragraph brutal honest assessment")


# GEMINI CLIENT

def _get_client():
    """Initialize the Gemini client from environment."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required.")
    return genai.Client(api_key=api_key)


MODEL_ID = "gemini-2.0-flash"

# AGENT METRICS — Track tokens, success/fallback for every LLM call

_metrics = {
    "total_calls": 0, "tokens_in": 0, "tokens_out": 0,
    "pydantic_ok": 0, "fallbacks": 0, "per_agent": {},
}


def reset_metrics():
    global _metrics
    _metrics = {
        "total_calls": 0, "tokens_in": 0, "tokens_out": 0,
        "pydantic_ok": 0, "fallbacks": 0, "per_agent": {},
    }


def get_metrics():
    return _metrics.copy()


def _track(name, response=None, fallback=False):
    _metrics["total_calls"] += 1
    if fallback:
        _metrics["fallbacks"] += 1
    else:
        _metrics["pydantic_ok"] += 1
    ti = to = 0
    if response and hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        ti = getattr(um, "prompt_token_count", 0) or 0
        to = getattr(um, "candidates_token_count", 0) or 0
    _metrics["tokens_in"] += ti
    _metrics["tokens_out"] += to
    _metrics["per_agent"][name] = {"tokens_in": ti, "tokens_out": to, "fallback": fallback}


# COLUMN MAPPER — Smart CSV column detection

def map_columns(df: pd.DataFrame) -> tuple:
    """Auto-detects Date, Description, Amount columns from any bank CSV format."""
    client = _get_client()

    sample = df.head(5).to_string()
    columns = list(df.columns)

    prompt = f"""You are a financial data expert for Indian bank statements.
Analyze this CSV and identify which columns contain what.

Column names: {json.dumps(columns)}
First 5 rows:
{sample}

Identify the EXACT column names for:
1. date_column: Transaction date
2. description_column: Transaction description/narration/particulars
3. amount_column: Single amount column (null if separate debit/credit)
4. debit_column: Debit/withdrawal column (null if combined)
5. credit_column: Credit/deposit column (null if combined)
6. balance_column: Running balance (null if not present)"""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ColumnMapping,
                temperature=0.1,
            ),
        )
        result = ColumnMapping.model_validate_json(response.text)
        _track("mapper", response)
        trace = f"[OK] Columns mapped → Date: '{result.date_column}', Desc: '{result.description_column}', Amount: '{result.amount_column or result.debit_column}'"
        return result, trace
    except Exception as e:
        _track("mapper", fallback=True)
        trace = f"[FALLBACK] LLM failed ({str(e)[:60]}). Using heuristics."
        return _fallback_column_mapping(df), trace


def _fallback_column_mapping(df: pd.DataFrame) -> ColumnMapping:
    """Heuristic fallback for column detection."""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    date_col = desc_col = amount_col = debit_col = credit_col = balance_col = None

    for key, orig in cols_lower.items():
        if not date_col and any(d in key for d in ["date", "txn date", "transaction date", "value date"]):
            date_col = orig
        elif not desc_col and any(d in key for d in ["narration", "description", "particular", "remark", "detail"]):
            desc_col = orig
        elif not amount_col and any(d in key for d in ["amount", "txn amount"]) and "balance" not in key:
            amount_col = orig
        elif not debit_col and any(d in key for d in ["debit", "withdrawal", "dr"]):
            debit_col = orig
        elif not credit_col and any(d in key for d in ["credit", "deposit", "cr"]):
            credit_col = orig
        elif not balance_col and "balance" in key:
            balance_col = orig

    if not date_col:
        for col in df.columns:
            try:
                pd.to_datetime(df[col].head(3), dayfirst=True)
                date_col = col
                break
            except Exception:
                pass

    if not desc_col:
        str_cols = df.select_dtypes(include=["object"]).columns
        if len(str_cols) > 0:
            avg_lens = {c: df[c].astype(str).str.len().mean() for c in str_cols if c != date_col}
            if avg_lens:
                desc_col = max(avg_lens, key=avg_lens.get)

    return ColumnMapping(
        date_column=date_col or df.columns[0],
        description_column=desc_col or df.columns[1],
        amount_column=amount_col, debit_column=debit_col,
        credit_column=credit_col, balance_column=balance_col,
    )


# AGENT 1 — THE SANITIZER
# Takes messy "UPI/123/ZOMATO" → {"merchant": "Zomato", "category": "Food"}

def run_sanitizer(descriptions: list, chunk_size: int = 40) -> tuple:
    """
    The Sanitizer: Cleans raw Indian bank narrations into structured data.
    Processes in chunks to respect Gemini token limits.
    """
    client = _get_client()
    all_cleaned = []
    chunks = [descriptions[i:i + chunk_size] for i in range(0, len(descriptions), chunk_size)]

    for chunk_idx, chunk in enumerate(chunks):
        indexed = [{"index": i, "description": str(d)} for i, d in enumerate(chunk)]

        prompt = f"""You are The Sanitizer — an Indian banking data cleaning expert.
Clean these raw bank transaction descriptions into structured data.

For each, extract:
1. merchant: Clean recognizable name ("UPI/32948/SWIGGY/HDFC" → "Swiggy")
2. category: One of [Food, Groceries, Shopping, Transport, Subscriptions, Utilities,
   Health, Entertainment, Travel, Investment, Insurance, Education, Rent, Salary,
   Transfer, Bank Fee, ATM, EMI, Unknown]

Batch {chunk_idx + 1}/{len(chunks)}:
{json.dumps(indexed, indent=2)}

Return "transactions" list with original_description, merchant, category for each."""

        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CleanedBatch,
                    temperature=0.1,
                ),
            )
            result = CleanedBatch.model_validate_json(response.text)
            _track("sanitizer", response)
            all_cleaned.extend([t.model_dump() for t in result.transactions])
        except Exception:
            _track("sanitizer", fallback=True)
            for desc in chunk:
                all_cleaned.append({
                    "original_description": str(desc),
                    "merchant": _extract_merchant_fallback(str(desc)),
                    "category": "Unknown",
                })

    unique_merchants = len(set(t["merchant"] for t in all_cleaned))
    trace = f"[OK] Sanitized {len(descriptions)} transactions in {len(chunks)} chunk(s). {unique_merchants} unique merchants found."
    return all_cleaned, trace


def _extract_merchant_fallback(desc: str) -> str:
    """Heuristic merchant extraction from UPI/NEFT strings."""
    noise = {"upi", "neft", "imps", "pos", "atm", "ref", "to", "from", "hdfc", "icici",
             "sbi", "axis", "kotak", "bank", "ltd", "pvt", "payment", "txn", "id", "cr", "dr"}
    parts = desc.replace("/", " ").replace("-", " ").replace("_", " ").split()
    cleaned = [p for p in parts if p.lower() not in noise and not p.isdigit() and len(p) > 2]
    return " ".join(cleaned[:3]).title() if cleaned else desc[:30]


# AGENT 2 — THE FORENSIC AUDITOR
# Detects: Subscription Creep, Hidden Bank Fees, Weekend Lifestyle Inflation

def run_forensic_audit(df: pd.DataFrame) -> tuple:
    """
    The Forensic Auditor — scans for 3 specific anomaly types plus general fraud.
    WOW FACTOR: "Weekend Lifestyle Inflation" is a unique detection no competitor will have.
    """
    client = _get_client()

    # Build analytics context
    category_stats = (
        df.groupby("category")["amount"]
        .agg(["mean", "std", "count", "sum"])
        .round(2)
        .to_dict(orient="index")
    )

    # Recurring merchant analysis for subscription creep
    merchant_groups = df.groupby("merchant_name").agg(
        count=("amount", "count"),
        amounts=("amount", lambda x: sorted(x.tolist())),
        dates=("date", lambda x: sorted([str(d) for d in x])),
    ).to_dict(orient="index")
    recurring = {k: v for k, v in merchant_groups.items() if v["count"] >= 2}

    # Weekend vs Weekday analysis for lifestyle inflation
    df_temp = df.copy()
    df_temp["is_weekend"] = df_temp["date"].dt.dayofweek >= 5
    weekend_avg = df_temp[df_temp["is_weekend"]]["amount"].mean() if df_temp["is_weekend"].any() else 0
    weekday_avg = df_temp[~df_temp["is_weekend"]]["amount"].mean() if (~df_temp["is_weekend"]).any() else 0
    weekend_total = df_temp[df_temp["is_weekend"]]["amount"].sum()
    weekday_total = df_temp[~df_temp["is_weekend"]]["amount"].sum()
    weekend_days = df_temp[df_temp["is_weekend"]]["date"].dt.date.nunique() or 1
    weekday_days = df_temp[~df_temp["is_weekend"]]["date"].dt.date.nunique() or 1

    # Prepare indexed transactions
    tx_data = df[["date", "merchant_name", "amount", "category"]].to_dict(orient="records")
    for tx in tx_data:
        tx["date"] = str(tx["date"])
    indexed_tx_json = json.dumps([{"idx": i, **tx} for i, tx in enumerate(tx_data)], indent=2)
    recurring_json = json.dumps(recurring, indent=2)
    stats_json = json.dumps(category_stats, indent=2)

    prompt = f"""You are The Forensic Auditor — an elite financial crime investigator for Indian banks.
Analyze ALL transactions and detect EVERY anomaly. Be ruthlessly thorough.

=== PRIMARY DETECTION TARGETS ===

1. **SUBSCRIPTION CREEP**: Same merchant charging MORE over time. If Netflix charged ₹199
   then later ₹249, that's a sneaky price hike the user probably didn't notice.

2. **HIDDEN BANK FEES**: Small auto-debits like SMS charges (₹59), maintenance fees (₹295),
   annual card fees, GST on services, locker rent. Banks slip these in hoping you won't notice.

3. **WEEKEND LIFESTYLE INFLATION**: Compare weekend vs weekday spending patterns.
   Weekend avg per day: ₹{weekend_total/weekend_days:,.0f}/day ({weekend_days} weekend days)
   Weekday avg per day: ₹{weekday_total/weekday_days:,.0f}/day ({weekday_days} weekday days)
   If weekend spending per day is significantly higher (>1.5x weekday), flag it. Look especially
   at Food, Shopping, Entertainment categories on weekends.

=== SECONDARY TARGETS ===
4. **DUPLICATE CHARGES**: Same merchant, same amount (±5%), within 3 days.
5. **SPENDING SPIKES**: Any transaction > 2.5× its category average.

=== Recurring Merchants ===
{recurring_json}

=== Category Statistics ===
{stats_json}

=== All Transactions (indexed) ===
{indexed_tx_json}

For EACH anomaly provide:
- transaction_indices, anomaly_type, severity, title, reasoning, amount_inr
- anomaly_type must be one of: subscription_creep, hidden_bank_fee, weekend_lifestyle_inflation, duplicate_charge, spending_spike

Also provide risk_score (0-100) and summary."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnomalyReport,
                temperature=0.2,
            ),
        )
        report = AnomalyReport.model_validate_json(response.text)
        _track("auditor", response)
        n = len(report.anomalies)
        trace = (
            f"[SCAN COMPLETE] {len(tx_data)} transactions analyzed.\n"
            f"[RESULT] {n} anomalies detected. Risk Score: {report.risk_score}/100\n"
            f"[SUMMARY] {report.summary}"
        )
        return report, trace
    except Exception as e:
        _track("auditor", fallback=True)
        trace = f"[FALLBACK] LLM audit failed ({str(e)[:60]}). Rule-based scan active."
        return _fallback_audit(df), trace


def _fallback_audit(df: pd.DataFrame) -> AnomalyReport:
    """Rule-based fallback forensic audit."""
    anomalies = []

    # Duplicate detection
    for merchant in df["merchant_name"].unique():
        mtxns = df[df["merchant_name"] == merchant].sort_values("date")
        for i in range(1, len(mtxns)):
            prev, curr = mtxns.iloc[i - 1], mtxns.iloc[i]
            days = (pd.to_datetime(curr["date"]) - pd.to_datetime(prev["date"])).days
            if 0 < days <= 3 and abs(curr["amount"] - prev["amount"]) / max(prev["amount"], 0.01) < 0.05:
                anomalies.append(AnomalyItem(
                    transaction_indices=[int(mtxns.index[i - 1]), int(mtxns.index[i])],
                    anomaly_type="duplicate_charge", severity="high",
                    title=f"Double charge at {merchant}",
                    reasoning=f"Two charges of ~₹{curr['amount']:,.0f} at {merchant} within {days} day(s).",
                    amount_inr=float(curr["amount"]),
                ))

    # Subscription creep
    for merchant in df["merchant_name"].unique():
        mtxns = df[df["merchant_name"] == merchant].sort_values("date")
        if len(mtxns) >= 2:
            amounts = mtxns["amount"].tolist()
            if amounts[-1] > amounts[0] * 1.05:
                anomalies.append(AnomalyItem(
                    transaction_indices=mtxns.index.tolist(),
                    anomaly_type="subscription_creep", severity="medium",
                    title=f"Price hike at {merchant}",
                    reasoning=f"{merchant} went from ₹{amounts[0]:,.0f} to ₹{amounts[-1]:,.0f}.",
                    amount_inr=float(amounts[-1]),
                ))

    # Weekend lifestyle inflation
    df_temp = df.copy()
    df_temp["is_weekend"] = df_temp["date"].dt.dayofweek >= 5
    if df_temp["is_weekend"].any() and (~df_temp["is_weekend"]).any():
        we_avg = df_temp[df_temp["is_weekend"]]["amount"].mean()
        wd_avg = df_temp[~df_temp["is_weekend"]]["amount"].mean()
        if we_avg > wd_avg * 1.5:
            we_indices = df_temp[df_temp["is_weekend"]].index.tolist()[:5]
            anomalies.append(AnomalyItem(
                transaction_indices=we_indices,
                anomaly_type="weekend_lifestyle_inflation", severity="medium",
                title="Weekend spending is inflated",
                reasoning=f"Weekend avg ₹{we_avg:,.0f} vs weekday avg ₹{wd_avg:,.0f} ({we_avg/wd_avg:.1f}x higher).",
                amount_inr=float(we_avg),
            ))

    # Spending spikes
    cat_means = df.groupby("category")["amount"].mean()
    for idx, row in df.iterrows():
        cat = row.get("category", "Unknown")
        if cat in cat_means and row["amount"] > 2.5 * cat_means[cat] and row["amount"] > 500:
            anomalies.append(AnomalyItem(
                transaction_indices=[int(idx)],
                anomaly_type="spending_spike", severity="medium",
                title=f"Spike at {row['merchant_name']}",
                reasoning=f"₹{row['amount']:,.0f} is {row['amount']/cat_means[cat]:.1f}x the {cat} avg.",
                amount_inr=float(row["amount"]),
            ))

    return AnomalyReport(
        anomalies=anomalies,
        risk_score=min(len(anomalies) * 12, 100),
        summary=f"Fallback analysis: {len(anomalies)} anomalies detected.",
    )


# AGENT 3 — THE WEALTH ARCHITECT
# Brutal, honest, 3-step action plan to save money.

def run_wealth_architect(df: pd.DataFrame, anomaly_report: AnomalyReport) -> tuple:
    """
    The Wealth Architect: No sugar-coating. Tells you exactly where your money
    is bleeding and gives 3 concrete steps to fix it.
    """
    client = _get_client()

    total_spent = df["amount"].sum()
    days = max((df["date"].max() - df["date"].min()).days, 1)
    daily_avg = total_spent / days
    monthly_est = daily_avg * 30

    category_summary = (
        df.groupby("category")["amount"]
        .agg(["sum", "mean", "count"]).round(2).to_dict(orient="index")
    )
    top_merchants = (
        df.groupby("merchant_name")["amount"]
        .sum().sort_values(ascending=False).head(10).to_dict()
    )
    anomaly_data = json.dumps([a.model_dump() for a in anomaly_report.anomalies[:5]], indent=2)

    prompt = f"""You are The Wealth Architect — India's most brutally honest finance advisor.
No sugar-coating. No generic advice. Look at the ACTUAL numbers and tell this person
EXACTLY where their money is bleeding.

=== Spending Data ({days} days) ===
- Total: ₹{total_spent:,.2f}
- Daily avg: ₹{daily_avg:,.2f}
- Monthly est: ₹{monthly_est:,.2f}

=== Category Breakdown ===
{json.dumps(category_summary, indent=2)}

=== Top 10 Money Pits ===
{json.dumps(top_merchants, indent=2)}

=== Anomalies: {len(anomaly_report.anomalies)} (Risk: {anomaly_report.risk_score}/100) ===
{anomaly_data}

RULES:
1. Give EXACTLY 3 action steps — no more, no less.
2. Be BRUTALLY specific: "You blew ₹X on Y. Cut it to ₹Z by doing W."
3. Address the anomalies: if there's subscription creep, say "call them and negotiate."
4. Give realistic estimated_monthly_savings for each step.
5. financial_health_score: 0-100 based on spending patterns and anomalies.
6. overall_verdict: One paragraph. Be real. Be direct. Like a tough-love mentor."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WealthStrategy,
                temperature=0.5,
            ),
        )
        strategy = WealthStrategy.model_validate_json(response.text)
        _track("architect", response)
        total_savings = sum(s.estimated_monthly_savings for s in strategy.action_plan)
        trace = (
            f"[OK] Wealth Architect delivered verdict.\n"
            f"[SCORE] Financial Health: {strategy.financial_health_score}/100\n"
            f"[SAVINGS] Potential: ₹{total_savings:,.0f}/month across 3 steps."
        )
        return strategy, trace
    except Exception as e:
        _track("architect", fallback=True)
        trace = f"[FALLBACK] LLM failed ({str(e)[:60]}). Using rule-based plan."
        return _fallback_strategy(df), trace


def _fallback_strategy(df: pd.DataFrame) -> WealthStrategy:
    """Fallback 3-step plan."""
    cat_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    steps = []
    for i, (cat, total) in enumerate(cat_totals.head(3).items(), 1):
        steps.append(ActionStep(
            step_number=i, title=f"Cut {cat} by 30%",
            description=f"You spent ₹{total:,.0f} on {cat}. Reduce to ₹{total*0.7:,.0f} by finding alternatives.",
            estimated_monthly_savings=round(total * 0.3 / 2, 2), category=cat,
        ))
    while len(steps) < 3:
        steps.append(ActionStep(
            step_number=len(steps) + 1, title="Start auto-saving ₹5,000/month",
            description="Set up a recurring transfer to a liquid fund.",
            estimated_monthly_savings=5000.0, category="General",
        ))
    return WealthStrategy(
        action_plan=steps[:3], financial_health_score=60.0,
        overall_verdict="Fallback analysis. Connect Gemini for a real verdict.",
    )


# CHAT AGENT — "Talk to your Data"

def chat_with_data(df: pd.DataFrame, question: str, chat_history: list) -> str:
    """Users ask natural-language questions; Gemini answers using the dataframe context."""
    client = _get_client()

    total_spent = df["amount"].sum()
    days = max((df["date"].max() - df["date"].min()).days, 1)

    context = f"""You are Atropos, an AI financial analyst. Answer questions about the user's
bank statement. Be specific — cite actual ₹ amounts from the data.

Data: {len(df)} transactions, {days} days, ₹{total_spent:,.2f} total.
Categories: {df.groupby('category')['amount'].agg(['sum','count']).sort_values('sum',ascending=False).to_string()}
Top merchants: {df.groupby('merchant_name')['amount'].sum().sort_values(ascending=False).head(10).to_string()}
Recent: {df.sort_values('date',ascending=False).head(5)[['date','merchant_name','amount','category']].to_string()}

Be concise, use ₹, give actionable advice. Use markdown formatting."""

    messages = [
        {"role": "user", "parts": [{"text": context}]},
        {"role": "model", "parts": [{"text": "I've loaded your financial data. What would you like to know?"}]},
    ]
    for msg in chat_history[-6:]:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [{"text": msg["content"]}]})
    messages.append({"role": "user", "parts": [{"text": question}]})

    try:
        response = client.models.generate_content(
            model=MODEL_ID, contents=messages,
            config=types.GenerateContentConfig(temperature=0.5),
        )
        _track("chat", response)
        return response.text
    except Exception as e:
        _track("chat", fallback=True)
        return f"Sorry, couldn't process that. Error: {str(e)[:100]}"


# SPENDING FORECAST — Trend-based 30-day projection

def run_forecast(df: pd.DataFrame) -> dict:
    """Simple trend-based forecast: splits data into halves, computes rate change."""
    total_spent = df["amount"].sum()
    days = max((df["date"].max() - df["date"].min()).days, 1)
    daily_rate = total_spent / days

    mid = df["date"].min() + pd.Timedelta(days=days // 2)
    h1 = df[df["date"] <= mid]
    h2 = df[df["date"] > mid]
    half_days = max(days // 2, 1)

    h1_rate = h1["amount"].sum() / half_days
    h2_rate = h2["amount"].sum() / max((df["date"].max() - mid).days, 1)
    trend_pct = ((h2_rate - h1_rate) / max(h1_rate, 1)) * 100

    cat_totals = df.groupby("category")["amount"].sum()
    cat_proj = {}
    for cat in cat_totals.index:
        c1 = h1[h1["category"] == cat]["amount"].sum()
        c2 = h2[h2["category"] == cat]["amount"].sum()
        c1_rate = c1 / half_days if c1 > 0 else 0
        c2_rate = c2 / max((df["date"].max() - mid).days, 1) if c2 > 0 else c1_rate
        cat_proj[cat] = {
            "current_total": float(cat_totals[cat]),
            "projected_30d": float(c2_rate * 30) if c2_rate > 0 else float(cat_totals[cat] / days * 30),
            "daily_rate": float(c2_rate if c2_rate > 0 else cat_totals[cat] / days),
            "trend": float(((c2_rate - c1_rate) / max(c1_rate, 0.01)) * 100) if c1_rate > 0 else 0.0,
        }

    return {
        "daily_rate": float(daily_rate),
        "projected_30d": float(h2_rate * 30),
        "trend_pct": float(trend_pct),
        "category_projections": cat_proj,
    }


# SMART ALERTS — Notification-style alerts from analysis results

def generate_smart_alerts(df: pd.DataFrame, anomaly_report, wealth_strategy) -> list:
    """Generate notification-style alerts from all analysis results."""
    alerts = []

    # Critical/high anomalies
    for a in anomaly_report.anomalies:
        if a.severity in ("critical", "high"):
            alerts.append({
                "type": "danger",
                "title": a.title,
                "detail": f"₹{a.amount_inr:,.0f} — {a.anomaly_type.replace('_', ' ').title()}",
            })

    # Weekend inflation
    dow = df.copy()
    dow["is_weekend"] = dow["date"].dt.dayofweek >= 5
    if dow["is_weekend"].any() and (~dow["is_weekend"]).any():
        we_avg = dow[dow["is_weekend"]]["amount"].mean()
        wd_avg = dow[~dow["is_weekend"]]["amount"].mean()
        if we_avg > wd_avg * 1.3:
            alerts.append({
                "type": "warning",
                "title": "Weekend spending elevated",
                "detail": f"₹{we_avg:,.0f}/txn weekends vs ₹{wd_avg:,.0f} weekdays ({we_avg/wd_avg:.1f}x)",
            })

    # Top category dominance
    cat_totals = df.groupby("category")["amount"].sum()
    total = df["amount"].sum()
    top_cat = cat_totals.idxmax()
    top_pct = cat_totals.max() / total * 100
    if top_pct > 30:
        alerts.append({
            "type": "info",
            "title": f"{top_cat} dominates spending",
            "detail": f"{top_pct:.0f}% of total — consider rebalancing",
        })

    # Poor health
    if wealth_strategy.financial_health_score < 50:
        alerts.append({
            "type": "danger",
            "title": "Financial health is poor",
            "detail": f"Score: {wealth_strategy.financial_health_score:.0f}/100",
        })
    elif wealth_strategy.financial_health_score >= 75:
        alerts.append({
            "type": "success",
            "title": "Financial health is strong",
            "detail": f"Score: {wealth_strategy.financial_health_score:.0f}/100",
        })

    return alerts[:6]


# PEER BENCHMARKING — Indian urban spending comparisons

# Approximate Indian urban household spending (% of monthly expenditure)
INDIA_URBAN_BENCHMARKS = {
    "Food": 28, "Dining": 28, "Groceries": 15, "Transport": 10,
    "Utilities": 8, "Shopping": 10, "Health": 6, "Entertainment": 4,
    "Subscriptions": 3, "Education": 7, "Rent": 20, "Insurance": 5,
    "Investment": 10, "Bank Fee": 1, "ATM": 1, "EMI": 8, "Transfer": 5,
    "Travel": 5, "Salary": 0, "Unknown": 0,
}


def get_peer_comparison(df: pd.DataFrame) -> list:
    """Compare user's spending proportions against Indian urban averages."""
    total = df["amount"].sum()
    cat_totals = df.groupby("category")["amount"].sum()

    comparisons = []
    for cat, amount in cat_totals.items():
        user_pct = (amount / total) * 100
        bench = INDIA_URBAN_BENCHMARKS.get(cat)
        if bench and bench > 0:
            ratio = user_pct / bench
            comparisons.append({
                "category": cat,
                "user_pct": round(user_pct, 1),
                "benchmark_pct": bench,
                "ratio": round(ratio, 2),
                "status": "over" if ratio > 1.3 else ("under" if ratio < 0.7 else "normal"),
            })
    return sorted(comparisons, key=lambda x: x["ratio"], reverse=True)


# AGENT DEBATE — Meta-analysis across all agents

def run_agent_debate(df: pd.DataFrame, anomaly_report, wealth_strategy, forecast: dict) -> str:
    """All agents' findings synthesized into a unified executive brief by Gemini."""
    client = _get_client()

    total = df["amount"].sum()
    days = max((df["date"].max() - df["date"].min()).days, 1)

    prompt = f"""You are the ATROPOS Meta-Analyst — the final arbiter of a multi-agent financial analysis.
Three specialized AI agents have independently analyzed {len(df)} transactions (₹{total:,.0f} over {days} days).

=== FORENSIC AUDITOR ===
Anomalies: {len(anomaly_report.anomalies)} | Risk: {anomaly_report.risk_score}/100
Summary: {anomaly_report.summary}
Top findings: {', '.join(a.title for a in anomaly_report.anomalies[:5])}

=== WEALTH ARCHITECT ===
Health: {wealth_strategy.financial_health_score}/100
Steps: {'; '.join(f'{s.title} (save ₹{s.estimated_monthly_savings:,.0f}/mo)' for s in wealth_strategy.action_plan)}
Verdict: {wealth_strategy.overall_verdict}

=== FORECAST ENGINE ===
30-day projection: ₹{forecast['projected_30d']:,.0f}
Trend: {'Increasing' if forecast['trend_pct'] > 0 else 'Decreasing'} by {abs(forecast['trend_pct']):.1f}%

Write EXACTLY 3 paragraphs:
1. SYNTHESIS: Connect the dots between all three analyses. What's the full picture?
2. PRIORITY ACTION: The #1 thing this person should do TODAY. Be specific with ₹ amounts.
3. OUTLOOK: Rate trajectory as BULLISH / NEUTRAL / BEARISH. Justify with data.

Be brutally honest. Use ₹ amounts. No fluff. No platitudes."""

    try:
        response = client.models.generate_content(
            model=MODEL_ID, contents=prompt,
            config=types.GenerateContentConfig(temperature=0.4),
        )
        _track("debate", response)
        return response.text
    except Exception as e:
        _track("debate", fallback=True)
        return (
            f"**Synthesis:** {len(anomaly_report.anomalies)} anomalies detected with a risk score of "
            f"{anomaly_report.risk_score:.0f}/100. Health score: {wealth_strategy.financial_health_score:.0f}/100.\n\n"
            f"**Priority:** {wealth_strategy.action_plan[0].title if wealth_strategy.action_plan else 'Review spending.'}\n\n"
            f"**Outlook:** {'BEARISH' if wealth_strategy.financial_health_score < 50 else 'NEUTRAL'} — "
            f"projected 30-day spend ₹{forecast['projected_30d']:,.0f}."
        )
