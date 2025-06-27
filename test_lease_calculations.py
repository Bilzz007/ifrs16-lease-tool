import pytest
import pandas as pd
from datetime import date
from typing import List
from lease_calculations import (
    calculate_right_of_use_asset,
    calculate_lease_liability,
    generate_lease_schedule,
    DepreciationMethod,
)


def test_cpi_escalation() -> None:
    start = date(2025, 1, 1)
    term = 24
    payment = 1000.0
    cpi = 3.0
    payments: List[float] = [round(payment * ((1 + cpi / 100) ** (m // 12)), 2) for m in range(term)]
    rate = 0.05
    liability = calculate_lease_liability(payments, rate)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, rate, term, rou)
    assert sum(df["Payment"]) == pytest.approx(sum(payments), abs=1.0)


def test_incentives_and_direct_costs() -> None:
    liability = 10000.0
    direct_costs = 500.0
    incentives = 300.0
    rou = calculate_right_of_use_asset(liability, direct_costs, incentives)
    assert rou == pytest.approx(10200.0, abs=1.0)


def test_residual_value_guarantee() -> None:
    start = date(2025, 1, 1)
    payments = [1000.0] * 23 + [1500.0]
    liability = calculate_lease_liability(payments, 0.06)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.06, 24, rou)
    assert float(df.iloc[-1]["Payment"]) == pytest.approx(1500.0, abs=1.0)


def test_short_term_lease() -> None:
    start = date(2025, 1, 1)
    short_term = 6
    payments = [2000.0] * short_term
    liability = calculate_lease_liability(payments, 0.04)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.04, short_term, rou)

    assert len(df) == 6
    assert float(df.iloc[-1]["Closing Liability"]) == pytest.approx(0.0, abs=0.01)
    assert float(df.iloc[-1]["ROU Balance"]) == pytest.approx(0.0, abs=0.01)


def test_custom_reporting_date() -> None:
    start = date(2025, 1, 1)
    term = 12
    payments = [1000.0] * term
    liability = calculate_lease_liability(payments, 0.05)
    rou = calculate_right_of_use_asset(liability)
    df, _ = generate_lease_schedule(start, payments, 0.05, term, rou)

    reporting_date = date(2025, 6, 30)
    df["Date"] = pd.to_datetime(df["Date"])
    ytd_dep = float(df[df["Date"] <= pd.to_datetime(reporting_date)]["Depreciation"].sum())
    assert ytd_dep > 0.0


def test_zero_discount_rate() -> None:
    payments = [1000.0] * 12
    liability = calculate_lease_liability(payments, 0.0)
    assert liability == pytest.approx(sum(payments), abs=1.0)


def test_prepayments() -> None:
    liability = 12000.0
    rou = calculate_right_of_use_asset(liability, direct_costs=500.0, incentives=0.0, prepayments=1000.0)
    assert rou == pytest.approx(13500.0, abs=1.0)


def test_sum_of_years_digits_depreciation() -> None:
    start = date(2025, 1, 1)
    rou = 24000.0
    term = 6
    payments = [4000.0] * term
    df, _ = generate_lease_schedule(
        start, payments, 0.05, term, rou, depreciation_method=DepreciationMethod.SUM_OF_YEARS
    )
    assert df["Depreciation"].sum() == pytest.approx(rou, abs=1.0)


def test_double_declining_depreciation() -> None:
    start = date(2025, 1, 1)
    rou = 24000.0
    term = 6
    payments = [4000.0] * term
    df, _ = generate_lease_schedule(
        start, payments, 0.05, term, rou, depreciation_method=DepreciationMethod.DOUBLE_DECLINING
    )
    assert df["Depreciation"].sum() == pytest.approx(rou, abs=1.0)


def test_input_validation() -> None:
    with pytest.raises(ValueError):
        calculate_right_of_use_asset(-1000.0)

    with pytest.raises(ValueError):
        calculate_lease_liability([], 0.05)
