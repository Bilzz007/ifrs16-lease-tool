import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict

# ---------------------- Lease Calculations ----------------------

def calculate_right_of_use_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_cpi_adjusted_payments(base_payment, term_months, annual_cpi_percent):
    cpi_rate = annual_cpi_percent / 100
    return [round(base_payment * ((1 + cpi_rate) ** (m // 12)), 2) for m in range(term_months)]

def calculate_lease_liability_from_payments(payments, rate):
    r = rate / 12
    return round(sum(p / ((1 + r) ** i) if r else p for i, p in enumerate(payments, start=1)), 2)

def generate_daily_depreciation_schedule(start_date, term_months, rou_asset):
    end_date = start_date + relativedelta(months=term_months)
    total_days = (end_date - start_date).days or 1
    daily_depr = rou_asset / total_days
    schedule = []
    cumulative = 0
    for i in range(term_months):
        m_start = start_date + relativedelta(months=i)
        m_end = m_start + relativedelta(months=1)
        days = (m_end - m_start).days
        depr = round(daily_depr * days, 2)
        if i == term_months - 1:
            depr = round(rou_asset - cumulative, 2)
            balance = 0
        else:
            balance = round(rou_asset - cumulative - depr, 2)
        cumulative += depr
        schedule.append((i + 1, m_start, depr, balance))
    return schedule

def generate_amortization_schedule(start_date, payments, rate, term_months, rou_asset):
    liability = calculate_lease_liability_from_payments(payments, rate)
    r = rate / 12
    depr_schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)
    schedule = []
    for i in range(term_months):
        pmt = payments[i]
        interest = round(liability * r, 2)
        principal = round(pmt - interest, 2)
        liability -= principal
        liability = 0 if abs(liability) < 1 else round(liability, 2)
        period, dt, depr, rou = depr_schedule[i]
        schedule.append({
            "Period": period, "Date": dt,
            "Payment": f"{pmt:,.0f}", "Interest": f"{interest:,.0f}",
            "Principal": f"{principal:,.0f}", "Closing Liability": f"{liability:,.0f}",
            "Depreciation": f"{depr:,.0f}", "Right-of-use Asset Closing Balance": f"{rou:,.0f}"
        })
    return pd.DataFrame(schedule), rou_asset
