import pandas as pd
import numpy as np
from typing import Optional


def load_and_parse_csv(uploaded_file) -> tuple:
    """
    Reads an uploaded CSV file and returns a raw DataFrame.
    Handles encoding issues, extra headers, and malformed data gracefully.

    Returns:
        tuple: (DataFrame or None, status message string)
    """
    try:
        # Try UTF-8 first (most common), fall back to latin-1 (handles special chars)
        try:
            df = pd.read_csv(uploaded_file, encoding="utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding="latin-1")

        if df.empty:
            return None, "❌ The uploaded CSV file is empty."

        if len(df.columns) < 2:
            return None, "❌ CSV must have at least 2 columns (date and description)."

        # Clean up: drop completely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")

        # Strip whitespace from column names
        df.columns = df.columns.str.strip()

        return df, f"✅ Loaded {len(df)} rows × {len(df.columns)} columns"

    except Exception as e:
        return None, f"❌ Failed to parse CSV: {str(e)[:200]}"


def standardize_dataframe(df: pd.DataFrame, mapping) -> tuple:
    """
    Standardizes a raw DataFrame using the AI-detected column mapping.
    Creates uniform columns: date, description, amount

    WOW FACTOR: Handles single-amount columns, separate debit/credit columns,
    ₹ symbols, commas in numbers — all the quirks of Indian bank CSVs.

    Returns:
        tuple: (standardized DataFrame or None, status message string)
    """
    try:
        result = pd.DataFrame()

        # Map date column
        result["date"] = pd.to_datetime(
            df[mapping.date_column], dayfirst=True, errors="coerce"
        )

        # Map description column
        result["description"] = df[mapping.description_column].astype(str).str.strip()

        # Map amount column(s)
        # Handle the 3 common formats: single amount, separate debit/credit, or auto-detect
        if mapping.amount_column and mapping.amount_column in df.columns:
            # Single amount column (e.g., HDFC format)
            result["amount"] = _clean_numeric(df[mapping.amount_column]).abs()

        elif mapping.debit_column and mapping.debit_column in df.columns:
            # Separate debit/credit columns (e.g., SBI, ICICI format)
            debit = _clean_numeric(df[mapping.debit_column]).fillna(0).abs()
            credit = pd.Series(0.0, index=df.index)

            if mapping.credit_column and mapping.credit_column in df.columns:
                credit = _clean_numeric(df[mapping.credit_column]).fillna(0).abs()

            # Use debit as primary spend amount; track credits separately
            result["amount"] = debit
            result["credit"] = credit
            result["is_credit"] = credit > 0

        else:
            # Last resort: find the best numeric column
            for col in df.columns:
                if col not in [mapping.date_column, mapping.description_column]:
                    vals = _clean_numeric(df[col])
                    if vals.notna().sum() > len(df) * 0.3:
                        result["amount"] = vals.abs()
                        break

        if "amount" not in result.columns:
            return None, "❌ Could not identify an amount column in your CSV."

        # Clean up
        # Only keep rows with valid date + amount, filter out zero-amount rows
        result = result.dropna(subset=["date", "amount"])
        result = result[result["amount"] > 0]
        result = result.sort_values("date").reset_index(drop=True)

        if len(result) == 0:
            return None, "❌ No valid transactions found after parsing."

        date_range = f"{result['date'].min().date()} to {result['date'].max().date()}"
        total = result["amount"].sum()
        info = (
            f"✅ Standardized {len(result)} transactions.\n"
            f"   Period: {date_range}\n"
            f"   Total debits: ₹{total:,.2f}"
        )
        return result, info

    except Exception as e:
        return None, f"❌ Standardization failed: {str(e)[:200]}"


def _clean_numeric(series: pd.Series) -> pd.Series:
    """Cleans a column to numeric — handles ₹ symbols, commas, spaces, Dr/Cr suffixes."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("INR", "", regex=False)
        .str.replace("Dr", "", regex=False)
        .str.replace("Cr", "", regex=False)
        .str.strip(),
        errors="coerce",
    )
