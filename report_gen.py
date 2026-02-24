from fpdf import FPDF
from datetime import datetime

class _AtroposPDF(FPDF):
    @staticmethod
    def _safe(text):
        """Replace Unicode chars that built-in fonts can't render."""
        return (str(text)
                .replace("\u20b9", "INR ")   # ₹
                .replace("\u2014", "-")       # —
                .replace("\u2013", "-")       # –
                .replace("\u2019", "'")       # '
                .replace("\u201c", '"')       # "
                .replace("\u201d", '"')       # "
                .replace("\u2018", "'"))      # '

    def header(self):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(30, 30, 30)
        self.cell(0, 12, "ATROPOS", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120)
        self.cell(0, 5, f"Financial Intelligence Report | {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150)
        self.cell(0, 10, f"ATROPOS Finance AI  |  Page {self.page_no()}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, self._safe(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def kv(self, key, value):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(80)
        self.cell(55, 6, self._safe(key))
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40)
        self.cell(0, 6, self._safe(value), new_x="LMARGIN", new_y="NEXT")

    def body_text(self, text):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60)
        self.multi_cell(0, 5, self._safe(text))
        self.ln(2)


def generate_pdf_report(df, anomaly_report, wealth_strategy, forecast=None):
    """Generate a styled PDF report. Returns bytes."""
    pdf = _AtroposPDF()
    total = df["amount"].sum()
    days = max((df["date"].max() - df["date"].min()).days, 1)

    # Page 1: Executive Summary + Findings
    pdf.add_page()
    pdf.section_title("Executive Summary")
    pdf.kv("Total Spent", f"INR {total:,.0f}")
    pdf.kv("Period", f"{days} days ({df['date'].min().date()} to {df['date'].max().date()})")
    pdf.kv("Transactions", str(len(df)))
    pdf.kv("Daily Average", f"INR {total / days:,.0f}")
    pdf.kv("Anomalies Detected", str(len(anomaly_report.anomalies)))
    pdf.kv("Risk Score", f"{anomaly_report.risk_score:.0f} / 100")
    pdf.kv("Health Score", f"{wealth_strategy.financial_health_score:.0f} / 100")
    pdf.ln(4)

    pdf.section_title(f"Forensic Findings ({len(anomaly_report.anomalies)})")
    pdf.body_text(anomaly_report.summary)

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_a = sorted(anomaly_report.anomalies, key=lambda x: sev_order.get(x.severity, 4))

    for a in sorted_a:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(
            200, 40, 40) if a.severity in ("critical", "high") else pdf.set_text_color(180, 120, 20)
        pdf.cell(0, 6, pdf._safe(f"[{a.severity.upper()}] {a.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(80)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(0, 5, pdf._safe(f"Type: {a.anomaly_type.replace('_',' ').title()}  |  Amount: INR {a.amount_inr:,.2f}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.body_text(a.reasoning)

    # Page 2: Action Plan
    pdf.add_page()
    pdf.section_title("Wealth Architect - Action Plan")
    total_sav = sum(s.estimated_monthly_savings for s in wealth_strategy.action_plan)
    pdf.kv("Potential Monthly Savings", f"INR {total_sav:,.0f}")
    pdf.ln(3)

    for step in wealth_strategy.action_plan:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(40)
        pdf.cell(0, 7, pdf._safe(f"Step {step.step_number}: {step.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.body_text(step.description)
        pdf.kv("Category", step.category)
        pdf.kv("Est. Monthly Savings", f"INR {step.estimated_monthly_savings:,.0f}")
        pdf.ln(3)

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(40)
    pdf.cell(0, 7, "Verdict", new_x="LMARGIN", new_y="NEXT")
    pdf.body_text(wealth_strategy.overall_verdict)

    # Page 3: Forecast
    if forecast:
        pdf.add_page()
        pdf.section_title("30-Day Spending Forecast")
        pdf.kv("Projected 30d Spend", f"INR {forecast['projected_30d']:,.0f}")
        trend_dir = "Up" if forecast["trend_pct"] > 0 else "Down"
        pdf.kv("Spending Trend", f"{trend_dir} {abs(forecast['trend_pct']):.1f}%")
        pdf.kv("Daily Burn Rate", f"INR {forecast['daily_rate']:,.0f}")
        pdf.ln(4)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(40)
        pdf.cell(0, 7, "Category Projections", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Table header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(45, 6, "Category", border=1, fill=True)
        pdf.cell(35, 6, "Current (INR)", border=1, fill=True, align="R")
        pdf.cell(35, 6, "Projected 30d", border=1, fill=True, align="R")
        pdf.cell(25, 6, "Trend", border=1, fill=True, align="R")
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for cat, data in sorted(forecast["category_projections"].items(),
                                key=lambda x: x[1]["projected_30d"], reverse=True):
            pdf.cell(45, 5, pdf._safe(str(cat)[:20]), border=1)
            pdf.cell(35, 5, f"{data['current_total']:,.0f}", border=1, align="R")
            pdf.cell(35, 5, f"{data['projected_30d']:,.0f}", border=1, align="R")
            t = data["trend"]
            pdf.cell(25, 5, f"{'+'if t>0 else ''}{t:.0f}%", border=1, align="R")
            pdf.ln()

    # Page 4: Category Breakdown
    pdf.add_page()
    pdf.section_title("Category Breakdown")

    cat_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    cat_counts = df.groupby("category")["amount"].count()

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(50, 6, "Category", border=1, fill=True)
    pdf.cell(35, 6, "Amount (INR)", border=1, fill=True, align="R")
    pdf.cell(25, 6, "% of Total", border=1, fill=True, align="R")
    pdf.cell(20, 6, "Txns", border=1, fill=True, align="R")
    pdf.cell(30, 6, "Avg (INR)", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for cat, amount in cat_totals.items():
        pct = amount / total * 100
        cnt = cat_counts.get(cat, 0)
        avg = amount / cnt if cnt > 0 else 0
        pdf.cell(50, 5, pdf._safe(str(cat)[:22]), border=1)
        pdf.cell(35, 5, f"{amount:,.0f}", border=1, align="R")
        pdf.cell(25, 5, f"{pct:.1f}%", border=1, align="R")
        pdf.cell(20, 5, str(cnt), border=1, align="R")
        pdf.cell(30, 5, f"{avg:,.0f}", border=1, align="R")
        pdf.ln()

    return bytes(pdf.output())
