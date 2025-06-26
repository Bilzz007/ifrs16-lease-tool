from lease_calculations import (
    calculate_right_of_use_asset,
    calculate_lease_liability,
    generate_lease_schedule,
)
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd

def assert_close(actual, expected, tol=1.0, label=""):
    assert abs(actual - expected) < tol, f"{label}: expected {expected}, got {actual}"

def run_tests():
    print("🧪 Running Enhanced IFRS 16 Test Suite...\n")

    # ---------------------- Test Case 1: CPI Escalation ----------------------
    start = date(2025, 1, 1)
    term = 24
    payment = 1000
    cpi = 3.0
    payments = [round(payment * ((1 + cpi / 100) ** (m // 12)), 2) for m in range(term)]
    rate = 0.05
    liability = calculate_lease_liability(payments, rate)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, rate, term, rou)
    assert_close(sum(df["Payment"].str.replace(",", "").astype(float)), sum(payments), label="CPI Total Payments")

    # ---------------------- Test Case 2: Incentives and Direct Costs ----------------------
    liability = 10000
    direct_costs = 500
    incentives = 300
    rou = calculate_right_of_use_asset(liability, direct_costs, incentives)
    assert_close(rou, 10200, label="ROU asset with adjustments")

    # ---------------------- Test Case 3: Residual Value Guarantee ----------------------
    payments = [1000] * 23 + [1500]  # $500 RVG in final month
    liability = calculate_lease_liability(payments, 0.06)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.06, 24, rou)
    last_payment = float(df.iloc[-1]["Payment"].replace(",", ""))
    assert_close(last_payment, 1500, label="RVG included in final payment")

    # ---------------------- Test Case 4: Short-Term Lease (6 Months) ----------------------
    short_term = 6
    payments = [2000] * short_term
    liability = calculate_lease_liability(payments, 0.04)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.04, short_term, rou)
    assert len(df) == 6, "Short-term lease should have 6 rows"
    assert_close(float(df.iloc[-1]["Closing Liability"].replace(",", "")), 0, label="Short lease liability zero")
    assert_close(float(df.iloc[-1]["Right-of-use Asset Closing Balance"].replace(",", "")), 0, label="Short lease ROU zero")

    # ---------------------- Test Case 5: Custom Reporting Date ----------------------
    reporting_date = date(2025, 6, 30)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Depreciation (num)"] = df["Depreciation"].str.replace(",", "").astype(float)
    ytd_dep = df[df["Date"] <= pd.to_datetime(reporting_date)]["Depreciation (num)"].sum()
    assert ytd_dep > 0, "Depreciation YTD must be non-zero for mid-year report"

    print("✅ All tests passed successfully.")

if __name__ == "__main__":
    run_tests()
