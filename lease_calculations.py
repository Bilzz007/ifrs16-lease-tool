from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Union
import pandas as pd
import numpy as np
from enum import Enum

class DepreciationMethod(Enum):
    STRAIGHT_LINE = "straight_line"
    SUM_OF_YEARS = "sum_of_years"
    DOUBLE_DECLINING = "double_declining"

class LeaseType(Enum):
    FINANCE = "finance"
    OPERATING = "operating"  # Remains for pre-IFRS 16 analysis

def calculate_right_of_use_asset(liability: float, direct_costs: float = 0, incentives: float = 0, prepayments: float = 0) -> float:
    """
    Calculate right-of-use asset with additional components
    Formula: Lease liability + Direct costs - Incentives + Prepayments
    """
    if any(x < 0 for x in [liability, direct_costs, incentives, prepayments]):
        raise ValueError("All financial inputs must be non-negative")
    return round(liability + direct_costs - incentives + prepayments, 2)

def generate_variable_payments(base_payment: float, term_months: int, 
                             adjustment_schedule: List[Tuple[int, float]] = None,
                             annual_cpi_percent: float = 0) -> List[float]:
    """
    Generate payment schedule with both CPI and custom adjustments
    adjustment_schedule: List of (month_index, adjustment_percent) tuples
    """
    payments = []
    cpi_factor = (1 + annual_cpi_percent / 100) ** (1/12)
    
    adjustment_dict = dict(adjustment_schedule) if adjustment_schedule else {}
    
    for m in range(term_months):
        payment = base_payment
        # Apply CPI adjustment (monthly compounding)
        if annual_cpi_percent:
            payment *= (cpi_factor ** (m + 1))
        # Apply custom adjustments
        if m in adjustment_dict:
            payment *= (1 + adjustment_dict[m]/100)
        payments.append(round(payment, 2))
    
    return payments

def calculate_lease_liability(payments: List[float], discount_rate: float, 
                            payment_timing: str = "end") -> float:
    """
    Calculate present value of lease payments with timing option
    payment_timing: 'start' or 'end' of period
    """
    if not payments:
        raise ValueError("Payments list cannot be empty")
    if discount_rate < 0:
        raise ValueError("Discount rate cannot be negative")
    
    r = discount_rate / 12
    if r == 0:  # Handle zero discount rate
        return round(sum(payments), 2)
    
    periods = np.arange(1, len(payments)+1) if payment_timing == "end" else np.arange(len(payments))
    discount_factors = 1 / ((1 + r) ** periods)
    return round(np.dot(payments, discount_factors), 2)

def generate_depreciation_schedule(start_date: date, term_months: int, rou_asset: float,
                                 method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
                                 residual_value: float = 0) -> List[Tuple[int, date, float, float]]:
    """
    Generate depreciation schedule with multiple methods
    Supports: Straight-line, Sum-of-years, Double-declining balance
    """
    if rou_asset <= 0:
        raise ValueError("ROU asset must be positive")
    if residual_value < 0 or residual_value >= rou_asset:
        raise ValueError("Residual value must be non-negative and less than ROU asset")
    
    depreciable_amount = rou_asset - residual_value
    schedule = []
    cumulative_depr = 0
    
    # Calculate monthly depreciation based on method
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
            # Ensure we don't depreciate below residual value
            if (book_value - depr) < residual_value:
                depr = book_value - residual_value
        
        # Final period adjustment
        if i == term_months - 1:
            depr = depreciable_amount - cumulative_depr
        
        depr = round(depr, 2)
        cumulative_depr += depr
        balance = round(rou_asset - cumulative_depr, 2)
        
        schedule.append((i + 1, current_date, depr, balance))
    
    return schedule

def generate_lease_schedule(start_date: date, payments: List[float], discount_rate: float,
                          term_months: int, rou_asset: float, 
                          depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
                          residual_value: float = 0) -> pd.DataFrame:
    """
    Comprehensive lease schedule generator with enhanced features
    Returns:
    - Amortization schedule DataFrame
    - Key lease metrics dictionary
    """
    # Validate inputs
    if len(payments) != term_months:
        raise ValueError("Payments list length must match lease term")
    
    # Calculate liability components
    liability = calculate_lease_liability(payments, discount_rate)
    interest_rate = discount_rate / 12
    
    # Generate depreciation schedule
    depr_schedule = generate_depreciation_schedule(
        start_date, term_months, rou_asset, depreciation_method, residual_value
    )
    
    # Build amortization schedule
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
    
    # Calculate key metrics
    total_payments = sum(payments)
    total_interest = sum(item["Interest"] for item in schedule)
    total_principal = sum(item["Principal"] for item in schedule)
    
    metrics = {
        "initial_liability": liability,
        "rou_asset": rou_asset,
        "total_payments": total_payments,
        "total_interest": total_interest,
        "effective_interest_rate": discount_rate,
        "depreciation_method": depreciation_method.value,
        "residual_value": residual_value
    }
    
    return pd.DataFrame(schedule), metrics

def calculate_lease_metrics(df: pd.DataFrame, reporting_date: date) -> dict:
    """
    Calculate key disclosure metrics for financial reporting
    """
    # Current year calculations
    cy_mask = df["Date"].dt.year == reporting_date.year
    cy_data = df[cy_mask]
    
    # Prior year calculations
    py_mask = df["Date"].dt.year == reporting_date.year - 1
    py_data = df[py_mask]
    
    # Liability maturity analysis
    def liability_maturity(df, ref_date):
        one_year_later = ref_date + relativedelta(years=1)
        mask = (df["Date"] > ref_date) & (df["Date"] <= one_year_later)
        current = df[mask]["Principal"].sum()
        non_current = df[df["Date"] > one_year_later]["Principal"].sum()
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
            "rou_balance": cy_data.iloc[-1]["ROU Balance"] if not cy_data.empty else 0
        },
        "prior_year": {
            "depreciation": py_data["Depreciation"].sum(),
            "interest": py_data["Interest"].sum(),
            "principal_payments": py_data["Principal"].sum(),
            "liability_current": py_current,
            "liability_noncurrent": py_noncurrent,
            "rou_balance": py_data.iloc[-1]["ROU Balance"] if not py_data.empty else 0
        }
    }

def handle_lease_modification(original_schedule: pd.DataFrame, modification_date: date,
                             new_payments: List[float], new_discount_rate: float,
                             new_direct_costs: float = 0, new_incentives: float = 0) -> pd.DataFrame:
    """
    Process a lease modification under IFRS 16
    Returns new combined schedule
    """
    # Split original schedule into pre/post modification
    pre_mod = original_schedule[original_schedule["Date"] < modification_date]
    post_mod = original_schedule[original_schedule["Date"] >= modification_date]
    
    # Calculate carrying amounts at modification date
    if not pre_mod.empty:
        remaining_liability = pre_mod.iloc[-1]["Closing Liability"]
        remaining_rou = pre_mod.iloc[-1]["ROU Balance"]
    else:
        remaining_liability = 0
        remaining_rou = 0
    
    # Calculate new ROU asset
    new_liability = calculate_lease_liability(new_payments, new_discount_rate)
    new_rou = calculate_right_of_use_asset(new_liability, new_direct_costs, new_incentives)
    
    # Adjust ROU asset for remaining balance
    adjusted_rou = remaining_rou + new_rou
    
    # Generate new schedule for modified payments
    term_months = len(new_payments)
    start_date = modification_date
    new_schedule, _ = generate_lease_schedule(
        start_date, new_payments, new_discount_rate, term_months, new_rou
    )
    
    # Combine schedules
    combined_schedule = pd.concat([pre_mod, new_schedule]).reset_index(drop=True)
    
    return combined_schedule
