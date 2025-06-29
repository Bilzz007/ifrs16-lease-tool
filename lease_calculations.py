# lease_calculations.py

from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Dict, Union, TypedDict
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

class LeaseRow(TypedDict):
    Period: int
    Date: date
    Payment: float
    Interest: float
    Principal: float
    Closing_Liability: float
    Depreciation: float
    ROU_Balance: float
    Total_Expense: float

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

    monthly_depr = 0.0
    remaining_months = 0
    sum_of_months = 0.0
    depreciation_rate = 0.0

    if method == DepreciationMethod.STRAIGHT_LINE:
        monthly_depr = depreciable_amount / term_months
    elif method == DepreciationMethod.SUM_OF_YEARS:
        remaining_months = term_months
        sum_of_months = term_months * (term_months + 1) / 2
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

    schedule: List[LeaseRow] = []
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
            "Closing_Liability": remaining_liability,
            "Depreciation": depr,
            "ROU_Balance": rou_balance,
            "Total_Expense": round(interest + depr, 2)
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

    cy_mask = df["Date"].dt.year == reporting_date.year
    py_mask = df["Date"].dt.year == reporting_date.year - 1

    cy_data = df[cy_mask]
    py_data = df[py_mask]

    def liability_maturity(df: pd.DataFrame, ref_date: date) -> Tuple[float, float]:
        one_year_later = ref_date + relativedelta(years=1)
        mask = (df["Date"] > pd.Timestamp(ref_date)) & (df["Date"] <= pd.Timestamp(one_year_later))
        current = df[mask]["Principal"].sum()
        non_current = df[df["Date"] > one_year_later]["Principal"].sum()
        return float(current), float(non_current)

    cy_current, cy_noncurrent = liability_maturity(df, reporting_date)
    py_current, py_noncurrent = liability_maturity(df, reporting_date - relativedelta(years=1))

    return {
        "current_year": {
            "depreciation": float(cy_data["Depreciation"].sum()),
            "interest": float(cy_data["Interest"].sum()),
            "principal_payments": float(cy_data["Principal"].sum()),
            "liability_current": cy_current,
            "liability_noncurrent": cy_noncurrent,
            "rou_balance": float(cy_data.iloc[-1]["ROU_Balance"]) if not cy_data.empty else 0.0
        },
        "prior_year": {
            "depreciation": float(py_data["Depreciation"].sum()),
            "interest": float(py_data["Interest"].sum()),
            "principal_payments": float(py_data["Principal"].sum()),
            "liability_current": py_current,
            "liability_noncurrent": py_noncurrent,
            "rou_balance": float(py_data.iloc[-1]["ROU_Balance"]) if not py_data.empty else 0.0
        }
    }

def handle_lease_modification(
    original_schedule: pd.DataFrame,
    modification_date: date,
    new_payments: List[float],
    new_discount_rate: float,
    rou_asset_remaining: float = None,
    direct_costs: float = 0,
    incentives: float = 0,
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
    residual_value: float = 0
) -> pd.DataFrame:
    """
    Handles IFRS 16 lease modification. Cuts original schedule at modification date,
    starts new schedule with revised terms from that date, joins for a continuous table.
    Returns the full new schedule (pre + post mod) for reporting.
    """
    # Ensure Date column is pandas datetime for robust comparison
    original_schedule["Date"] = pd.to_datetime(original_schedule["Date"])

    # Schedules pre- and post-modification
    pre_mod = original_schedule[original_schedule["Date"] < pd.Timestamp(modification_date)]

    # Carrying values at modification date
    if not pre_mod.empty:
        last_row = pre_mod.iloc[-1]
        opening_liability = float(last_row["Closing_Liability"])
        opening_rou = rou_asset_remaining if rou_asset_remaining is not None else float(last_row["ROU_Balance"])
    else:
        opening_liability = 0.0
        opening_rou = rou_asset_remaining if rou_asset_remaining is not None else 0.0

    # New ROU for mod: liability (+ direct costs - incentives), as per IFRS 16
    new_liability = calculate_lease_liability(new_payments, new_discount_rate)
    new_rou = calculate_right_of_use_asset(new_liability, direct_costs, incentives)

    # For depreciation, IFRS 16 requires adjust ROU for any mod effect (no remeasurement if new lease)
    rou_asset_for_new_schedule = opening_rou + (new_rou - opening_liability)  # Per IFRS 16 para 38

    # Start date is modification date, term is new
    term_months = len(new_payments)
    new_schedule, _ = generate_lease_schedule(
        modification_date,
        new_payments,
        new_discount_rate,
        term_months,
        rou_asset_for_new_schedule,
        depreciation_method,
        residual_value
    )

    # Reset periods to continue after pre_mod
    pre_mod_rows = pre_mod.copy()
    new_schedule_rows = new_schedule.copy()
    if not pre_mod_rows.empty:
        last_period = pre_mod_rows["Period"].iloc[-1]
        new_schedule_rows["Period"] = new_schedule_rows["Period"] + last_period

    # Combine for a full schedule
    combined = pd.concat([pre_mod_rows, new_schedule_rows], ignore_index=True)
    return combined
