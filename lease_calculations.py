from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Dict, Union
import pandas as pd
import numpy as np
from enum import Enum


class DepreciationMethod(Enum):
    STRAIGHT_LINE = "straight_line"
    SUM_OF_YEARS = "sum_of_years"
    DOUBLE_DECLINING = "double_declining"


class LeaseType(Enum):
    FINANCE = "finance"
    OPERATING = "operating"


def calculate_right_of_use_asset(
    liability: float,
    direct_costs: float = 0,
    incentives: float = 0,
    prepayments: float = 0
) -> float:
    amounts = [float(liability), float(direct_costs), float(incentives), float(prepayments)]
    if any(x < 0 for x in amounts):
        raise ValueError("All financial inputs must be non-negative")
    return round(liability + direct_costs - incentives + prepayments, 2)


def generate_variable_payments(
    base_payment: float,
    term_months: int,
    adjustment_schedule: List[Tuple[int, float]] = None,
    annual_cpi_percent: float = 0
) -> List[float]:
    payments = []
    cpi_factor = (1 + annual_cpi_percent / 100) ** (1 / 12)
    adjustment_dict = dict(adjustment_schedule) if adjustment_schedule else {}

    for m in range(term_months):
        payment = base_payment
        if annual_cpi_percent:
            payment *= (cpi_factor ** (m + 1))
        if m in adjustment_dict:
            payment *= (1 + adjustment_dict[m] / 100)
        payments.append(round(payment, 2))
    return payments


def calculate_lease_liability(
    payments: List[float],
    discount_rate: float,
    payment_timing: str = "end"
) -> float:
    if not payments:
        raise ValueError("Payments list cannot be empty")
    if discount_rate < 0:
        raise ValueError("Discount rate cannot be negative")

    r = discount_rate / 12
    if r == 0:
        return round(sum(payments), 2)

    periods = np.arange(1, len(payments) + 1) if payment_timing == "end" else np.arange(len(payments))
    discount_factors = 1 / ((1 + r) ** periods)
    return round(float(np.dot(np.array(payments), discount_factors)), 2)


def generate_depreciation_schedule(
    start_date: date,
    term_months: int,
    rou_asset: float,
    method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
    residual_value: float = 0
) -> List[Tuple[int, date, float, float]]:
    if rou_asset <= 0:
        raise ValueError("ROU asset must be positive")
    if residual_value < 0 or residual_value >= rou_asset:
        raise ValueError("Residual value must be non-negative and less than ROU asset")

    depreciable_amount = rou_asset - residual_value
    schedule = []
    cumulative_depr = 0.0

    if method == DepreciationMethod.STRAIGHT_LINE:
        monthly_depr = depreciable_amount / term_months
    elif method == DepreciationMethod.SUM_OF_YEARS:
        total_months = term_months
        sum_of_months = total_months * (total_months + 1) / 2
        remaining_months = term_months
    elif method == DepreciationMethod.DOUBLE_DECLINING:
        straight_line_rate = 1 / term_months
        depreciation_rate = 2 * straight_line_rate

    for i in range(term_months):
        current_date = start_date + relativedelta(months=i)
        if method == DepreciationMethod.STRAIGHT_LINE:
            depr = monthly_depr
        elif method == DepreciationMethod.SUM_OF_YEARS:
            depr = (remaining_months / sum_of_months) * depreciable_amount
            remaining_months -= 1
        elif method == DepreciationMethod.DOUBLE_DECLINING:
            book_value = rou_asset - cumulative_depr
            depr = book_value * depreciation_rate
            if (book_value - depr) < residual_value:
                depr = book_value - residual_value

        if i == term_months - 1:
            depr = depreciable_amount - cumulative_depr

        depr = round(depr, 2)
        cumulative_depr += depr
        balance = round(rou_asset - cumulative_depr, 2)
        schedule.append((i + 1, current_date, depr, balance))

    return schedule


def generate_lease_schedule(
    start_date: date,
    payments: List[float],
    discount_rate: float,
    term_months: int,
    rou_asset: float,
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
    residual_value: float = 0
) -> Tuple[pd.DataFrame, Dict[str, Union[float, str]]]:
    if len(payments) != term_months:
        raise ValueError("Payments list length must match lease term")

    liability = calculate_lease_liability(payments, discount_rate)
    interest_rate = discount_rate / 12
    depr_schedule = generate_depreciation_schedule(start_date, term_months, rou_asset, depreciation_method, residual_value)

    schedule = []
    remaining_liability = liability

    for i in range(term_months):
        payment = payments[i]
        interest = round(remaining_liability * interest_rate, 2)
        principal = round(payment - interest, 2)
        remaining_liability -= principal
        remaining_liability = max(0, round(remaining_liability, 2))

        period, dt, depr, rou_balance = depr_schedule[i]
        schedule.append({
            "Period": period,
            "Date": dt,
            "Payment": payment,
            "Interest": interest,
            "Principal": principal,
            "Closing Liability": remaining_liability,
            "Depreciation": depr,
            "ROU Balance": rou_balance,
            "Total Expense": round(interest + depr, 2)
        })

    metrics: Dict[str, Union[float, str]] = {
        "initial_liability": liability,
        "rou_asset": rou_asset,
        "total_payments": sum(payments),
        "total_interest": sum(item["Interest"] for item in schedule),
        "effective_interest_rate": discount_rate,
        "depreciation_method": depreciation_method.value,
        "residual_value": residual_value,
    }

    return pd.DataFrame(schedule), metrics


def calculate_lease_metrics(df: pd.DataFrame, reporting_date: date) -> Dict[str, Dict[str, float]]:
    df["Date"] = pd.to_datetime(df["Date"])

    cy_mask: pd.Series[bool] = df["Date"].dt.year == reporting_date.year
    py_mask: pd.Series[bool] = df["Date"].dt.year == reporting_date.year - 1

    cy_data = df[cy_mask]
    py_data = df[py_mask]

    def liability_maturity(df: pd.DataFrame, ref_date: date) -> Tuple[float, float]:
        date_series = pd.to_datetime(df["Date"])
        ref_ts = pd.Timestamp(ref_date)
        one_year_later = pd.Timestamp(ref_date + relativedelta(years=1))

        mask = (date_series > ref_ts) & (date_series <= one_year_later)
        current = float(df.loc[mask, "Principal"].sum())
        non_current = float(df.loc[date_series > one_year_later, "Principal"].sum())
        return current, non_current

    cy_current, cy_noncurrent = liability_maturity(df, reporting_date)
    py_current, py_noncurrent = liability_maturity(df, reporting_date - relativedelta(years=1))

    return {
        "current_year": {
            "depreciation": cy_data["Depreciation"].sum(),
            "interest": cy_data["Interest"].sum(),
            "principal_payments": cy_data["Principal"].sum(),
            "liability_current": cy_current,
            "liability_noncurrent": cy_noncurrent,
            "rou_balance": cy_data.iloc[-1]["ROU Balance"] if not cy_data.empty else 0.0
        },
        "prior_year": {
            "depreciation": py_data["Depreciation"].sum(),
            "interest": py_data["Interest"].sum(),
            "principal_payments": py_data["Principal"].sum(),
            "liability_current": py_current,
            "liability_noncurrent": py_noncurrent,
            "rou_balance": py_data.iloc[-1]["ROU Balance"] if not py_data.empty else 0.0
        }
    }


def handle_lease_modification(
    original_schedule: pd.DataFrame,
    modification_date: date,
    new_payments: List[float],
    new_discount_rate: float,
    new_direct_costs: float = 0,
    new_incentives: float = 0
) -> pd.DataFrame:
    pre_mod = original_schedule[original_schedule["Date"] < modification_date]

    remaining_liability = float(pre_mod.iloc[-1]["Closing Liability"]) if not pre_mod.empty else 0.0
    remaining_rou = float(pre_mod.iloc[-1]["ROU Balance"]) if not pre_mod.empty else 0.0

    new_liability = calculate_lease_liability(new_payments, new_discount_rate)
    new_rou = calculate_right_of_use_asset(new_liability, new_direct_costs, new_incentives)
    adjusted_rou = remaining_rou + new_rou

    term_months = len(new_payments)
    start_date = modification_date

    new_schedule, _ = generate_lease_schedule(
        start_date, new_payments, new_discount_rate, term_months, new_rou
    )

    combined_schedule = pd.concat([pre_mod, new_schedule]).reset_index(drop=True)
    return combined_schedule
