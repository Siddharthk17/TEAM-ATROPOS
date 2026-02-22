import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


def generate_mock_transactions() -> pd.DataFrame:
    """
    Generates a realistic 60-day Indian bank statement for demo mode.
    Returns a DataFrame pre-formatted for the Aura pipeline.
    """
    random.seed(42)
    np.random.seed(42)

    end_date = datetime(2026, 2, 20).date()
    start_date = end_date - timedelta(days=60)

    transactions = []
    tx_id = 1

    # MERCHANT PROFILES — realistic Indian merchants with spend ranges
    merchant_profiles = {
        # Subscriptions (monthly)
        "Netflix": {
            "cat": "Subscriptions",
            "micro": "Video Streaming",
            "min": 649,
            "max": 649,
        },
        "Spotify": {
            "cat": "Subscriptions",
            "micro": "Music Streaming",
            "min": 119,
            "max": 119,
        },
        "Amazon Prime": {
            "cat": "Subscriptions",
            "micro": "Prime Membership",
            "min": 299,
            "max": 299,
        },
        "Disney+ Hotstar": {
            "cat": "Subscriptions",
            "micro": "Video Streaming",
            "min": 299,
            "max": 299,
        },
        # Dining / Food Delivery
        "Swiggy": {"cat": "Dining", "micro": "Food Delivery", "min": 150, "max": 600},
        "Zomato": {"cat": "Dining", "micro": "Food Delivery", "min": 200, "max": 700},
        "Dominos Pizza": {
            "cat": "Dining",
            "micro": "Fast Food",
            "min": 300,
            "max": 800,
        },
        "Starbucks": {"cat": "Dining", "micro": "Cafe", "min": 250, "max": 550},
        # Groceries
        "BigBasket": {
            "cat": "Groceries",
            "micro": "Online Grocery",
            "min": 500,
            "max": 3000,
        },
        "Blinkit": {
            "cat": "Groceries",
            "micro": "Quick Commerce",
            "min": 200,
            "max": 1500,
        },
        "DMart": {"cat": "Groceries", "micro": "Supermarket", "min": 1000, "max": 5000},
        # Utilities
        "Tata Power": {
            "cat": "Utilities",
            "micro": "Electricity Bill",
            "min": 1200,
            "max": 3500,
        },
        "Jio Fiber": {
            "cat": "Utilities",
            "micro": "Internet Bill",
            "min": 999,
            "max": 999,
        },
        "Mahanagar Gas": {
            "cat": "Utilities",
            "micro": "Gas Bill",
            "min": 400,
            "max": 800,
        },
        # Transport
        "Uber India": {
            "cat": "Transport",
            "micro": "Ride Hailing",
            "min": 100,
            "max": 500,
        },
        "Ola Cabs": {
            "cat": "Transport",
            "micro": "Ride Hailing",
            "min": 80,
            "max": 450,
        },
        "Delhi Metro": {"cat": "Transport", "micro": "Metro", "min": 30, "max": 60},
        # Shopping
        "Amazon.in": {
            "cat": "Shopping",
            "micro": "E-Commerce",
            "min": 500,
            "max": 8000,
        },
        "Flipkart": {"cat": "Shopping", "micro": "E-Commerce", "min": 400, "max": 6000},
        "Myntra": {"cat": "Shopping", "micro": "Fashion", "min": 800, "max": 4000},
        # Health
        "Apollo Pharmacy": {
            "cat": "Health",
            "micro": "Pharmacy",
            "min": 200,
            "max": 1500,
        },
        "Practo Consultation": {
            "cat": "Health",
            "micro": "Doctor Consultation",
            "min": 500,
            "max": 1000,
        },
        # Entertainment
        "PVR Cinemas": {
            "cat": "Entertainment",
            "micro": "Movies",
            "min": 300,
            "max": 800,
        },
        "BookMyShow": {
            "cat": "Entertainment",
            "micro": "Events & Movies",
            "min": 200,
            "max": 1500,
        },
    }

    # GENERATE NORMAL TRANSACTIONS
    current_date = start_date
    while current_date <= end_date:
        daily_merchants = []

        if current_date.weekday() < 5 and random.random() < 0.7:
            daily_merchants.append("Delhi Metro")
        if random.random() < 0.5:
            daily_merchants.append(random.choice(["Swiggy", "Zomato"]))
        if random.random() < 0.3:
            daily_merchants.append(random.choice(["Uber India", "Ola Cabs"]))

        day_of_week = current_date.weekday()
        if day_of_week == 5:
            if random.random() < 0.6:
                daily_merchants.append(random.choice(["BigBasket", "Blinkit", "DMart"]))
            if random.random() < 0.3:
                daily_merchants.append(random.choice(["Amazon.in", "Flipkart"]))
            if random.random() < 0.4:
                daily_merchants.append(random.choice(["Dominos Pizza", "Starbucks"]))
        if day_of_week in [5, 6] and random.random() < 0.2:
            daily_merchants.append(random.choice(["PVR Cinemas", "BookMyShow"]))

        # Monthly subscriptions
        if current_date.day == 1:
            daily_merchants.extend(["Netflix", "Spotify"])
        elif current_date.day == 3:
            daily_merchants.append("Amazon Prime")
        elif current_date.day == 5:
            daily_merchants.append("Disney+ Hotstar")

        # Utilities
        if current_date.day == 10:
            daily_merchants.append("Tata Power")
        if current_date.day == 12:
            daily_merchants.append("Jio Fiber")
        if current_date.day == 15:
            daily_merchants.append("Mahanagar Gas")

        if current_date.day == 20 and random.random() < 0.4:
            daily_merchants.append(
                random.choice(["Apollo Pharmacy", "Practo Consultation"])
            )
        if current_date.day == 25 and random.random() < 0.3:
            daily_merchants.append("Myntra")
        if random.random() < 0.2:
            daily_merchants.append("Blinkit")

        for merchant in daily_merchants:
            profile = merchant_profiles[merchant]
            amount = round(random.uniform(profile["min"], profile["max"]), 2)
            transactions.append(
                {
                    "transaction_id": tx_id,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": f"UPI/{random.randint(10000, 99999)}/{merchant.upper().replace(' ', '')}/HDFC",
                    "merchant_name": merchant,
                    "amount": amount,
                    "micro_cat": profile["micro"],
                    "category": profile["cat"],
                    "location": "India",
                }
            )
            tx_id += 1

        current_date += timedelta(days=1)

    # INJECT ANOMALIES

    # ANOMALY 1: Duplicate Netflix charge 2 days after the real one
    netflix_dates = [t["date"] for t in transactions if t["merchant_name"] == "Netflix"]
    if netflix_dates:
        dup_date = (
            datetime.strptime(netflix_dates[0], "%Y-%m-%d") + timedelta(days=2)
        ).strftime("%Y-%m-%d")
        transactions.append(
            {
                "transaction_id": tx_id,
                "date": dup_date,
                "description": "UPI/88421/NETFLIX/HDFC",
                "merchant_name": "Netflix",
                "amount": 649.0,
                "micro_cat": "Video Streaming",
                "category": "Subscriptions",
                "location": "India",
            }
        )
        tx_id += 1

    # ANOMALY 2: Subscription Creep — Spotify price hike ₹119 → ₹149
    # Find the second Spotify charge and bump its price
    spotify_txns = [t for t in transactions if t["merchant_name"] == "Spotify"]
    if len(spotify_txns) >= 2:
        spotify_txns[-1]["amount"] = 149.0
        spotify_txns[-1]["description"] = "UPI/77832/SPOTIFY/HDFC"

    # ANOMALY 3: Hidden Bank Fees
    fee_date1 = (start_date + timedelta(days=15)).strftime("%Y-%m-%d")
    transactions.append(
        {
            "transaction_id": tx_id,
            "date": fee_date1,
            "description": "SMS ALERT CHARGES Q3 2025-26",
            "merchant_name": "HDFC Bank SMS Charges",
            "amount": 59.0,
            "micro_cat": "SMS Alert Fee",
            "category": "Bank Fee",
            "location": "India",
        }
    )
    tx_id += 1

    fee_date2 = (start_date + timedelta(days=30)).strftime("%Y-%m-%d")
    transactions.append(
        {
            "transaction_id": tx_id,
            "date": fee_date2,
            "description": "AMC/MAINTENANCE/CHARGE/HDFC/DEBITCARD",
            "merchant_name": "HDFC Debit Card AMC",
            "amount": 295.0,
            "micro_cat": "Card Maintenance Fee",
            "category": "Bank Fee",
            "location": "India",
        }
    )
    tx_id += 1

    # ANOMALY 4: Suspicious foreign transaction — ₹45,000 in Paris
    foreign_date = (start_date + timedelta(days=35)).strftime("%Y-%m-%d")
    transactions.append(
        {
            "transaction_id": tx_id,
            "date": foreign_date,
            "description": "POS/LUXE BOUTIQUE/PARIS/FRANCE/EUR",
            "merchant_name": "LUXE BOUTIQUE PARIS",
            "amount": 45000.0,
            "micro_cat": "International Purchase",
            "category": "Shopping",
            "location": "France",
        }
    )
    tx_id += 1

    # ANOMALY 5: Food delivery spike — 5 high-value orders in one day
    spike_date = (start_date + timedelta(days=45)).strftime("%Y-%m-%d")
    for _ in range(5):
        m = random.choice(["Swiggy", "Zomato"])
        transactions.append(
            {
                "transaction_id": tx_id,
                "date": spike_date,
                "description": f"UPI/{random.randint(10000, 99999)}/{m.upper()}/HDFC",
                "merchant_name": m,
                "amount": round(random.uniform(800, 1500), 2),
                "micro_cat": "Food Delivery",
                "category": "Dining",
                "location": "India",
            }
        )
        tx_id += 1

    # ANOMALY 6: Suspicious unknown merchant with coded name
    weird_date = (start_date + timedelta(days=50)).strftime("%Y-%m-%d")
    transactions.append(
        {
            "transaction_id": tx_id,
            "date": weird_date,
            "description": "POS/XTRM_PAY_7829/UNKNOWN/IND",
            "merchant_name": "XTRM_PAY_7829",
            "amount": 12499.0,
            "micro_cat": "Unknown Purchase",
            "category": "Unknown",
            "location": "India",
        }
    )
    tx_id += 1

    # BUILD FINAL DATAFRAME
    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["date", "transaction_id"]).reset_index(drop=True)

    return df


if __name__ == "__main__":
    df = generate_mock_transactions()
    print(f"Generated {len(df)} transactions over 60 days")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Total spent: ₹{df['amount'].sum():,.2f}")
    print(f"\nAnomalies included: duplicate charge, subscription creep, hidden fees,")
    print(f"  foreign transaction, spending spike, suspicious merchant")
    print(f"\nCategories: {df['macro_category'].value_counts().to_dict()}")
