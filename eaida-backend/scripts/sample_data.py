"""Generate a sample dataset so you can test every endpoint immediately."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 1200

df = pd.DataFrame({
    "customer_id": range(1, n + 1),
    "age": rng.integers(18, 70, n),
    "tenure_months": rng.integers(1, 72, n),
    "monthly_charges": rng.normal(70, 25, n).round(2).clip(10),
    "support_tickets": rng.poisson(1.5, n),
    "contract": rng.choice(["month-to-month", "one-year", "two-year"], n, p=[.55, .3, .15]),
    "region": rng.choice(["north", "south", "east", "west"], n),
    "signup_date": pd.to_datetime("2021-01-01") + pd.to_timedelta(rng.integers(0, 1400, n), "D"),
})
score = (0.03 * df.monthly_charges - 0.04 * df.tenure_months
         + 0.5 * df.support_tickets + (df.contract == "month-to-month") * 1.5)
df["churn"] = (score + rng.normal(0, 1, n) > 2.2).astype(int)
df.loc[rng.choice(n, 60, replace=False), "monthly_charges"] = np.nan

df.to_csv("storage/sample_customers.csv", index=False)
print(f"Wrote storage/sample_customers.csv  shape={df.shape}  churn_rate={df.churn.mean():.2%}")