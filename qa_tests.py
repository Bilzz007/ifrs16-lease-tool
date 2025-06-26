from lease_calculations import (
    calculate_right_of_use_asset,
    calculate_lease_liability,
    generate_lease_schedule,
    DepreciationMethod,
)
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd
from typing import Sequence


def assert_close(actual: float, expected: float, tol: float = 1.0, label: str = "") -> None:
    assert abs(actual - expected) < tol, f"{label}: expected {expected}, got {actual}"


def run_tests() -> None:
    print("🧪 Running Enhanced IFRS 16 Test Suite...\n")

    # ---------------------- Test Case 1: CPI Escalation ----------------------
    start: date = date(2025, 1, 1)
    term: int = 24
    payment: float = 1000.0
    cpi: float = 3.0
    payments: list[float] = [round(payment * ((1 + cpi / 100) ** (m // 12)), 2) for m in range(term)]
    rate: float = 0.05
    liability: float = calculate_lease_liability(payments, rate)
    rou: float = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, rate, term, rou)
    assert_close(sum(df["Payment"]), sum(payments), label="CPI Total Payments")

    # ---------------------- Test Case 2: Incentives and Direct Costs ----------------------
    liability = 10000.0
    direct_costs = 500.0
    incentives = 300.0
    rou = calculate_right_of_use_asset(liability, direct_costs, incentives)
    assert_close(rou, 10200, label="ROU asset with adjustments")

    # ---------------------- Test Case 3: Residual Value Guarantee ----------------------
    payments = [1000.0] * 23 + [1500.0]  # $500 RVG in final month
    liability = calculate_lease_liability(payments, 0.06)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.06, 24, rou)
    last_payment = df.iloc[-1]["Payment"]
    assert_close(last_payment, 1500, label="RVG included in final payment")

    # ---------------------- Test Case 4: Short-Term Lease (6 Months) ----------------------
    short_term = 6
    payments = [2000.0] * short_term
    liability = calculate_lease_liability(payments, 0.04)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.04, short_term, rou)
    assert len(df) == 6, "Short-term lease should have 6 rows"
    assert_close(df.iloc[-1]["Closing Liability"], 0, label="Short lease liability zero")
    assert_close(df.iloc[-1]["ROU Balance"], 0, label="Short lease ROU zero")

    # ---------------------- Test Case 5: Custom Reporting Date ----------------------
    reporting_date = date(2025, 6, 30)
    df["Date"] = pd.to_datetime(df["Date"])
    ytd_dep = df[df["Date"] <= pd.to_datetime(reporting_date)]["Depreciation"].sum()
    assert ytd_dep > 0, "Depreciation YTD must be non-zero for mid-year report"

    # ---------------------- Test Case 6: Zero Discount Rate ----------------------
    payments = [1000.0] * 12
    liability = calculate_lease_liability(payments, 0.0)
    assert_close(liability, sum(payments), label="Zero discount rate liability")

    # ---------------------- Test Case 7: Prepayments ----------------------
    liability = 12000.0
    rou = calculate_right_of_use_asset(liability, direct_costs=500, incentives=0, prepayments=1000)
    assert_close(rou, 13500, label="ROU with prepayments")

    # ---------------------- Test Case 8: Sum-of-Years Digits Depreciation ----------------------
    rou = 24000.0
    term = 6
    df, _ = generate_lease_schedule(
        start,
        [4000.0] * term,
        0.05,
        term,
        rou,
        depreciation_method=DepreciationMethod.SUM_OF_YEARS,
    )
    assert abs(df["Depreciation"].sum() - rou) < 1, "SOYD should fully depreciate asset"

    # ---------------------- Test Case 9: Double-Declining Depreciation ----------------------
    df, _ = generate_lease_schedule(
        start,
        [4000.0] * term,
        0.05,
        term,
        rou,
        depreciation_method=DepreciationMethod.DOUBLE_DECLINING,
    )
    assert abs(df["Depreciation"].sum() - rou) < 1, "Double-declining should fully depreciate asset"

    # ---------------------- Test Case 10: Input Validation ----------------------
    try:
        calculate_right_of_use_asset(-1000.0)
        assert False, "Negative liability should raise error"
    except ValueError:
        pass

    try:
        calculate_lease_liability([], 0.05)
        assert False, "Empty payments list should raise error"
    except ValueError:
        pass

    print("✅ All tests passed successfully.")


if __name__ == "__main__":
    run_tests()
