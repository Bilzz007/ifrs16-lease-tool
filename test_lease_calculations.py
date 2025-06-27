from lease_calculations import (
    calculate_right_of_use_asset,
    calculate_lease_liability,
    generate_lease_schedule,
    DepreciationMethod,
)
from datetime import date
import pandas as pd
from typing import List


def assert_close(actual: float, expected: float, tol: float = 1.0, label: str = "") -> None:
    assert abs(actual - expected) < tol, f"{label}: expected {expected}, got {actual}"


def test_cpi_escalation() -> None:
    start: date = date(2025, 1, 1)
    term: int = 24
    payment: float = 1000.0
    cpi: float = 3.0
    payments: List[float] = [round(payment * ((1 + cpi / 100) ** (m // 12)), 2) for m in range(term)]
    rate: float = 0.05
    liability: float = calculate_lease_liability(payments, rate)
    rou: float = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, rate, term, rou)
    assert_close(sum(df["Payment"]), sum(payments), label="CPI Total Payments")


def test_incentives_and_direct_costs() -> None:
    liability = 10000.0
    direct_costs = 500.0
    incentives = 300.0
    rou = calculate_right_of_use_asset(liability, direct_costs, incentives)
    assert_close(rou, 10200.0, label="ROU asset with adjustments")


def test_residual_value_guarantee() -> None:
    start = date(2025, 1, 1)
    payments = [1000.0] * 23 + [1500.0]
    liability = calculate_lease_liability(payments, 0.06)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.06, 24, rou)
    last_payment: float = float(df.iloc[-1]["Payment"])
    assert_close(last_payment, 1500.0, label="RVG included in final payment")


def test_short_term_lease() -> None:
    start = date(2025, 1, 1)
    short_term: int = 6
    payments = [2000.0] * short_term
    liability = calculate_lease_liability(payments, 0.04)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.04, short_term, rou)
    assert len(df) == 6, "Short-term lease should have 6 rows"
    assert_close(float(df.iloc[-1]["Closing Liability"]), 0.0, label="Short lease liability zero")
    assert_close(float(df.iloc[-1]["ROU Balance"]), 0.0, label="Short lease ROU zero")


def test_reporting_date_depreciation() -> None:
    start = date(2025, 1, 1)
    payments = [1000.0] * 12
    liability = calculate_lease_liability(payments, 0.05)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.05, 12, rou)
    reporting_date: date = date(2025, 6, 30)
    df["Date"] = pd.to_datetime(df["Date"])
    ytd_dep: float = float(df[df["Date"] <= pd.to_datetime(reporting_date)]["Depreciation"].sum())
    assert ytd_dep > 0.0, "Depreciation YTD must be non-zero for mid-year report"


def test_zero_discount_rate() -> None:
    payments = [1000.0] * 12
    liability = calculate_lease_liability(payments, 0.0)
    assert_close(liability, sum(payments), label="Zero discount rate liability")


def test_rou_with_prepayments() -> None:
    liability = 12000.0
    rou = calculate_right_of_use_asset(liability, direct_costs=500.0, incentives=0.0, prepayments=1000.0)
    assert_close(rou, 13500.0, label="ROU with prepayments")


def test_sum_of_years_digits_depreciation() -> None:
    start = date(2025, 1, 1)
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


def test_double_declining_depreciation() -> None:
    start = date(2025, 1, 1)
    rou = 24000.0
    term = 6
    df, _ = generate_lease_schedule(
        start,
        [4000.0] * term,
        0.05,
        term,
        rou,
        depreciation_method=DepreciationMethod.DOUBLE_DECLINING,
    )
    assert abs(df["Depreciation"].sum() - rou) < 1, "Double-declining should fully depreciate asset"


def test_input_validation() -> None:
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
